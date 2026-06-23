"""Simulation Service — end-to-end backtest for the simulation dashboard.

Pipeline (causally honest):
    1. Fetch historical OHLCV for [start - lookback, end].
    2. Build technical features (reusing PredictionService feature prep).
    3. Train the chosen model on rows strictly BEFORE start_date.
    4. Walk forward across [start_date, end_date]: predict next-day close,
       derive the predicted return, and apply threshold trading rules.
    5. Account a single-asset cash+shares portfolio and compute metrics.

The frontend (SimulationDashboard.js) consumes the SimulationResult shape:
portfolio_metrics, prediction_accuracy, time_series, transaction_history.

No model is persisted — this is an in-memory backtest. The pretrained-model
path falls back to training a fresh model of the requested family on the
in-window training data (loading arbitrary saved estimators is out of scope
and environment-dependent).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import joblib
import numpy as np
import pandas as pd
import httpx
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
import xgboost as xgb
import lightgbm as lgb

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services.prediction_service import PredictionService
from app.models.schemas import (
    SimulationRequest,
    SimulationResult,
    SimulationPortfolioMetrics,
    SimulationPredictionAccuracy,
    SimulationTimePoint,
    SimulationTransaction,
)

settings = get_settings()
logger = logging.getLogger(__name__)

# Trading days per year for annualising the Sharpe ratio.
_TRADING_DAYS = 252

# History (calendar days) fetched before start_date to train on + warm up features.
_TRAIN_LOOKBACK_DAYS = 400


class SimulationError(Exception):
    """Raised when a simulation cannot be run (e.g. insufficient data)."""


def _build_model(display_name: Optional[str]):
    """Map a simulation-dashboard display name to a fresh sklearn-style model."""
    name = (display_name or "").strip().lower()
    if name in ("xgboost", "xgb"):
        return xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1)
    if name in ("lightgbm", "lgbm", "lgb"):
        return lgb.LGBMRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, verbose=-1)
    if name in ("random forest", "random_forest", "randomforest"):
        return RandomForestRegressor(n_estimators=100, max_depth=10)
    # Linear Regression, LSTM (no torch here), and unknowns → linear baseline.
    return LinearRegression()


class SimulationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._pred = PredictionService(session)

    async def _fetch_range(self, symbol: str, start: str, end: str) -> Optional[pd.DataFrame]:
        """Fetch OHLCV for an explicit date range from stock-data-service."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}/api/v2/stocks/{symbol}/history",
                    params={"start_date": start, "end_date": end},
                    timeout=60.0,
                )
            if resp.status_code != 200:
                logger.warning("history fetch %s returned %s", symbol, resp.status_code)
                return None
            payload = resp.json()
            data = payload.get("data") if isinstance(payload, dict) else payload
            if not data:
                return None
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values("date").reset_index(drop=True)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to fetch range for %s: %s", symbol, e)
            return None

    async def run_simulation(self, req: SimulationRequest) -> SimulationResult:
        # When the user ticks "use a pretrained model", load and walk the solution's
        # SAVED model forward instead of training a fresh one in-window.
        if req.use_pretrained_model and req.pretrained_solution_id:
            return await self._run_with_pretrained(req)

        start = pd.Timestamp(req.start_date)
        end = pd.Timestamp(req.end_date)
        if end <= start:
            raise SimulationError("end_date must be after start_date")

        fetch_start = (start - timedelta(days=_TRAIN_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
        fetch_end = end.strftime("%Y-%m-%d")
        df = await self._fetch_range(req.ticker, fetch_start, fetch_end)
        if df is None or len(df) < 80:
            raise SimulationError(
                f"Insufficient historical data for {req.ticker} "
                f"({0 if df is None else len(df)} rows; need ≥ 80)"
            )

        # Feature engineering (reuses the production feature builder).
        feat = self._pred._prepare_features(df)
        feature_cols = self._pred._get_feature_columns(feat)
        if not feature_cols:
            raise SimulationError("No usable features after preparation")

        train_mask = feat["date"] < start
        sim_mask = (feat["date"] >= start) & (feat["date"] <= end)
        train_df = feat[train_mask]
        sim_df = feat[sim_mask].reset_index(drop=True)

        if len(train_df) < 30:
            raise SimulationError(
                f"Insufficient training rows before {req.start_date} "
                f"({len(train_df)}; need ≥ 30). Pick a later start date."
            )
        if len(sim_df) < 2:
            raise SimulationError("Simulation window too short (need ≥ 2 trading days)")

        model = _build_model(req.model_type)
        model.fit(train_df[feature_cols], train_df["target"])
        preds = np.asarray(model.predict(sim_df[feature_cols]), dtype=float)

        return self._simulate_trading(req, sim_df, preds, feature_cols)

    # ── Pretrained-model path ──────────────────────────────────────────────────

    async def _load_solution_indicators(self, solution_id: int) -> list:
        """Load the indicator rows configured for a solution (same query training uses)."""
        from sqlalchemy import text
        result = await self.session.execute(
            text(
                """
                SELECT si.indicator_id, si.indicator_category, si.covariate_type, si.parameters,
                       ti.name, ti.type, ti.default_parameters, ti.calculation_function
                FROM solution_indicators si
                LEFT JOIN technical_indicators ti ON si.indicator_id = ti.id
                WHERE si.solution_id = :sid
                """
            ),
            {"sid": solution_id},
        )
        return [dict(r) for r in result.mappings().all()]

    async def _run_with_pretrained(self, req: SimulationRequest) -> SimulationResult:
        """Backtest using the solution's SAVED trained model (no in-window retraining).

        Loads the joblib artifact persisted by solution training and rebuilds features
        exactly the way that training did (the shared ``_build_feature_df`` plus the
        solution's configured indicators), then walks the saved model forward across the
        window. This is a true out-of-sample test of the model the user actually trained.
        """
        # Lazy import keeps the (heavy) routes module out of package import time and
        # avoids any import cycle; these are pure feature-builder helpers.
        from app.api.solution_routes import _build_feature_df, _prepare_indicator_features

        sid = req.pretrained_solution_id
        model_file = os.path.join(settings.MODEL_PATH, f"solution_{sid}_model.joblib")
        if not os.path.exists(model_file):
            raise SimulationError(
                f"No saved model for solution {sid}. Train the solution first, then re-run."
            )
        try:
            artifact = joblib.load(model_file)
        except Exception as e:  # noqa: BLE001
            raise SimulationError(f"Failed to load saved model for solution {sid}: {e}")

        model = artifact.get("model")
        feature_cols = artifact.get("feature_cols") or []
        if model is None or not feature_cols:
            raise SimulationError(f"Saved model for solution {sid} is incomplete; retrain it.")

        saved_ticker = artifact.get("ticker")
        if saved_ticker and saved_ticker != req.ticker:
            raise SimulationError(
                f"Solution {sid} was trained on {saved_ticker}, not {req.ticker}. "
                f"Pick {saved_ticker} or train a solution for {req.ticker}."
            )

        start = pd.Timestamp(req.start_date)
        end = pd.Timestamp(req.end_date)
        if end <= start:
            raise SimulationError("end_date must be after start_date")

        fetch_start = (start - timedelta(days=_TRAIN_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
        df = await self._fetch_range(req.ticker, fetch_start, end.strftime("%Y-%m-%d"))
        if df is None or len(df) < 80:
            raise SimulationError(
                f"Insufficient historical data for {req.ticker} "
                f"({0 if df is None else len(df)} rows; need ≥ 80)"
            )

        # Rebuild features the SAME way solution training did (indicators included),
        # so the saved model sees the feature distribution it was fit on.
        dfi = (
            df.set_index("date")[["open", "high", "low", "close", "volume"]]
            .apply(pd.to_numeric, errors="coerce")
            .dropna()
        )
        indicator_rows = await self._load_solution_indicators(sid)
        ind_feat, _ = _prepare_indicator_features(dfi, indicator_rows)
        feat = _build_feature_df(dfi, ind_feat)
        feat["target"] = feat["close"].shift(-1)
        feat = feat.dropna().reset_index()  # restore 'date' as a column

        missing = [c for c in feature_cols if c not in feat.columns]
        if missing:
            raise SimulationError(
                f"Saved model expects features that can't be reproduced now: {missing}. "
                f"Retrain solution {sid}."
            )

        sim_df = feat[(feat["date"] >= start) & (feat["date"] <= end)].reset_index(drop=True)
        if len(sim_df) < 2:
            raise SimulationError("Simulation window too short (need ≥ 2 trading days)")

        # Training fit on numpy arrays, so predict on .values too (no feature-name check).
        preds = np.asarray(model.predict(sim_df[feature_cols].values), dtype=float)

        # Reflect the real model in the result (e.g. "BlockRNN" rather than the default).
        req.model_type = artifact.get("model_type") or req.model_type
        logger.info(
            "Simulation (pretrained) solution=%s ticker=%s model=%s sim_rows=%d",
            sid, req.ticker, req.model_type, len(sim_df),
        )
        return self._simulate_trading(req, sim_df, preds, feature_cols)

    # ── Trading engine ─────────────────────────────────────────────────────────

    def _simulate_trading(
        self,
        req: SimulationRequest,
        sim_df: pd.DataFrame,
        preds: np.ndarray,
        feature_cols: list,
    ) -> SimulationResult:
        tp = req.trading_params
        cash = float(req.initial_capital)
        shares = 0.0
        cost_basis = 0.0   # avg cost of currently-held shares

        time_series: list[SimulationTimePoint] = []
        transactions: list[SimulationTransaction] = []
        portfolio_values: list[float] = []

        wins = 0
        closed_trades = 0
        dir_correct = 0
        dir_total = 0
        ape_sum = 0.0
        ape_n = 0

        for i in range(len(sim_df)):
            row = sim_df.iloc[i]
            close = float(row["close"])
            actual_next = float(row["target"])
            pred_next = float(preds[i])
            date_str = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")

            # Prediction-accuracy bookkeeping (vs the next-day actual).
            if close > 0:
                if np.sign(pred_next - close) == np.sign(actual_next - close):
                    dir_correct += 1
                dir_total += 1
            if actual_next != 0:
                ape_sum += abs(actual_next - pred_next) / abs(actual_next)
                ape_n += 1

            predicted_return = (pred_next - close) / close if close > 0 else 0.0

            # --- Trading rules ---
            if predicted_return >= tp.threshold_buy and cash > 0:
                spend = cash * tp.position_size
                if spend > 0 and close > 0:
                    bought = spend / close
                    new_total = shares + bought
                    cost_basis = (
                        (cost_basis * shares + close * bought) / new_total
                        if new_total > 0 else 0.0
                    )
                    shares = new_total
                    cash -= spend
                    pv = cash + shares * close
                    transactions.append(SimulationTransaction(
                        date=date_str, type="BUY", price=round(close, 2),
                        shares=round(bought, 2), total_value=round(spend, 2),
                        portfolio_value=round(pv, 2), cash_balance=round(cash, 2),
                    ))
            elif predicted_return <= tp.threshold_sell and shares > 0:
                proceeds = shares * close
                if cost_basis > 0 and close > cost_basis:
                    wins += 1
                closed_trades += 1
                cash += proceeds
                sold = shares
                shares = 0.0
                cost_basis = 0.0
                pv = cash + shares * close
                transactions.append(SimulationTransaction(
                    date=date_str, type="SELL", price=round(close, 2),
                    shares=round(sold, 2), total_value=round(proceeds, 2),
                    portfolio_value=round(pv, 2), cash_balance=round(cash, 2),
                ))

            pv = cash + shares * close
            portfolio_values.append(pv)
            time_series.append(SimulationTimePoint(
                date=date_str,
                actual_price=round(close, 2),
                predicted_price=round(pred_next, 2),
            ))

        metrics = self._compute_metrics(
            req, sim_df, portfolio_values, wins, closed_trades, len(transactions)
        )
        accuracy = SimulationPredictionAccuracy(
            direction_accuracy=round(100.0 * dir_correct / dir_total, 2) if dir_total else 0.0,
            mape=round(100.0 * ape_sum / ape_n, 2) if ape_n else 0.0,
        )
        return SimulationResult(
            ticker=req.ticker,
            model_type=req.model_type or "XGBoost",
            portfolio_metrics=metrics,
            prediction_accuracy=accuracy,
            time_series=time_series,
            transaction_history=transactions,
        )

    @staticmethod
    def _compute_metrics(
        req: SimulationRequest,
        sim_df: pd.DataFrame,
        portfolio_values: list,
        wins: int,
        closed_trades: int,
        total_trades: int,
    ) -> SimulationPortfolioMetrics:
        initial = float(req.initial_capital)
        final = float(portfolio_values[-1]) if portfolio_values else initial
        total_return = final - initial
        total_return_pct = (total_return / initial * 100.0) if initial else 0.0

        pv = np.asarray(portfolio_values, dtype=float)
        # Daily portfolio returns → annualised Sharpe (rf = 0).
        if len(pv) > 1:
            daily = np.diff(pv) / pv[:-1]
            std = float(np.std(daily))
            sharpe = float(np.mean(daily) / std * np.sqrt(_TRADING_DAYS)) if std > 0 else 0.0
            running_max = np.maximum.accumulate(pv)
            drawdowns = (pv - running_max) / running_max
            max_dd = float(np.min(drawdowns) * 100.0)   # most negative
        else:
            sharpe = 0.0
            max_dd = 0.0

        # Buy & hold benchmark over the same window → alpha.
        first_close = float(sim_df.iloc[0]["close"])
        last_close = float(sim_df.iloc[-1]["close"])
        bh_pct = ((last_close - first_close) / first_close * 100.0) if first_close else 0.0
        alpha = total_return_pct - bh_pct

        win_rate = (100.0 * wins / closed_trades) if closed_trades else 0.0

        return SimulationPortfolioMetrics(
            initial_capital=round(initial, 2),
            final_value=round(final, 2),
            total_return=round(total_return, 2),
            total_return_pct=round(total_return_pct, 2),
            total_trades=total_trades,
            win_rate=round(win_rate, 2),
            sharpe_ratio=round(sharpe, 2),
            max_drawdown=round(max_dd, 2),
            alpha=round(alpha, 2),
        )
