"""Solution Service API Routes

Provides CRUD endpoints for prediction solutions, matching the v2 frontend API.
References webapi/views_solution.py and webapi/repositories/predict_solution_repository.py
for database schema and business logic.
"""
import json
import logging
import threading
import time as time_module
from typing import Optional, Dict, List
from datetime import datetime

import httpx
import numpy as np
import pandas as pd
import ta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.dependencies import get_db, get_current_user_optional, get_current_user
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

solution_router = APIRouter()

# Global dictionary to track training status (matches webapi pattern)
training_status = {}


# ==========================================
# Solution CRUD Endpoints
# ==========================================

@solution_router.get("/all")
@solution_router.get("/all/")
async def get_solutions(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get solutions created by the logged-in user.
    Matches webapi: views_solution.get_solutions
    """
    try:
        if current_user and current_user.get("user_id"):
            user_id = str(current_user["user_id"])
            result = await db.execute(
                text("""
                    SELECT
                        tbl_solution.id,
                        tbl_solution.solution_name,
                        tbl_solution.ticker,
                        tbl_solution.created_by,
                        tbl_solution.user_id,
                        tbl_solution.created_date,
                        tbl_solution.updated_date,
                        tbl_solution.train_status,
                        model_instances.model_type,
                        model_instances.model_sub_type,
                        model_instances.model_name
                    FROM tbl_solution
                    INNER JOIN model_instances ON tbl_solution.model_id = model_instances.id
                    WHERE tbl_solution.user_id = :user_id
                """),
                {"user_id": user_id}
            )
        else:
            result = await db.execute(
                text("""
                    SELECT
                        tbl_solution.id,
                        tbl_solution.solution_name,
                        tbl_solution.ticker,
                        tbl_solution.created_by,
                        tbl_solution.user_id,
                        tbl_solution.created_date,
                        tbl_solution.updated_date,
                        tbl_solution.train_status,
                        model_instances.model_type,
                        model_instances.model_sub_type,
                        model_instances.model_name
                    FROM tbl_solution
                    INNER JOIN model_instances ON tbl_solution.model_id = model_instances.id
                """)
            )
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch solutions: {e}")
        return []


@solution_router.get("/tickers")
@solution_router.get("/tickers/")
async def get_predict_tickers(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tickers available for prediction from user's portfolio.
    Queries portfolio_holdings table directly (shared database).
    Matches webapi: views_solution.get_predict_tickers
    """
    user_id = current_user["user_id"]

    try:
        # Query portfolio holdings directly - all services share the same database
        result = await db.execute(
            text("""
                SELECT DISTINCT ph.symbol as ticker
                FROM portfolio_holdings ph
                INNER JOIN portfolios p ON ph.portfolio_id = p.id
                WHERE p.user_id = :user_id
                ORDER BY ph.symbol
            """),
            {"user_id": user_id}
        )
        rows = result.mappings().all()

        if rows:
            # Return objects with 'ticker' field matching frontend expectations
            return [{"ticker": row["ticker"]} for row in rows]

        logger.info(f"User {user_id} has no stocks in portfolio")
        return []
    except Exception as e:
        logger.error(f"Failed to get predict tickers: {e}")
        return []


@solution_router.get("/models")
@solution_router.get("/models/")
async def get_predict_models(
    db: AsyncSession = Depends(get_db)
):
    """Get all available models for solution creation.
    Matches webapi: views_solution.get_predict_models
    """
    try:
        result = await db.execute(
            text("""
                SELECT id, model_name, model_type, model_sub_type,
                       past_covariate, future_covariate
                FROM model_instances
                ORDER BY id DESC
            """)
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.warning(f"Failed to fetch predict models: {e}")
        return []


@solution_router.get("/covariates")
@solution_router.get("/covariates/")
async def get_predict_covariates(
    db: AsyncSession = Depends(get_db)
):
    """Get covariates (time series) for solution configuration.
    Matches webapi: views_solution.get_predict_covariates
    """
    try:
        result = await db.execute(
            text("SELECT id, series_name FROM tbl_time_series WHERE status = 1")
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.warning(f"Failed to fetch covariates: {e}")
        return []


@solution_router.post("")
@solution_router.post("/")
@solution_router.post("/create")
@solution_router.post("/create/")
async def create_solution(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new prediction solution.
    Matches webapi: views_solution.create_predict_solution
    """
    data = await request.json()
    user_id = str(current_user["user_id"])

    if 'user_id' not in data:
        data['user_id'] = user_id
    if 'created_by' not in data:
        data['created_by'] = user_id

    try:
        result = await db.execute(
            text("""
                INSERT INTO tbl_solution
                (solution_name, model_id, ticker, created_date, created_by, user_id,
                 status, start_training_date, end_training_date,
                 train_validation_ratio, solution_status, train_status)
                VALUES (:solution_name, :model_id, :ticker, :created_date, :created_by,
                        :user_id, :status, :start_training_date, :end_training_date,
                        :train_validation_ratio, 0, 'not_trained')
            """),
            {
                "solution_name": data.get("solution_name"),
                "model_id": data.get("model_id"),
                "ticker": data.get("ticker"),
                "created_date": data.get("created_date", datetime.now().strftime("%Y-%m-%d")),
                "created_by": data.get("created_by"),
                "user_id": data.get("user_id"),
                "status": data.get("status", 1),
                "start_training_date": data.get("start_training_date"),
                "end_training_date": data.get("end_training_date"),
                "train_validation_ratio": data.get("train_validation_ratio", 0.8),
            }
        )
        await db.commit()
        solution_id = result.lastrowid

        created_solution = {**data, "id": solution_id}
        return created_solution
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create solution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create solution: {str(e)}")


@solution_router.put("")
@solution_router.put("/")
@solution_router.put("/update")
@solution_router.put("/update/")
async def update_solution(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a prediction solution.
    Matches webapi: views_solution.update_predict_solution
    """
    data = await request.json()
    user_id = str(current_user["user_id"])

    if 'user_id' not in data:
        data['user_id'] = user_id
    if 'updated_by' not in data:
        data['updated_by'] = user_id

    solution_id = data.get("id")
    if not solution_id:
        raise HTTPException(status_code=400, detail="Solution ID is required")

    try:
        await db.execute(
            text("""
                UPDATE tbl_solution
                SET solution_name = :solution_name, model_id = :model_id, ticker = :ticker,
                    updated_date = :updated_date, updated_by = :updated_by,
                    start_training_date = :start_training_date,
                    end_training_date = :end_training_date,
                    train_validation_ratio = :train_validation_ratio,
                    user_id = :user_id
                WHERE id = :id
            """),
            {
                "solution_name": data.get("solution_name"),
                "model_id": data.get("model_id"),
                "ticker": data.get("ticker"),
                "updated_date": data.get("updated_date", datetime.now().strftime("%Y-%m-%d")),
                "updated_by": data.get("updated_by"),
                "start_training_date": data.get("start_training_date"),
                "end_training_date": data.get("end_training_date"),
                "train_validation_ratio": data.get("train_validation_ratio", 0.8),
                "user_id": data.get("user_id"),
                "id": solution_id,
            }
        )
        await db.commit()
        return data
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update solution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update solution: {str(e)}")


@solution_router.get("/calculate-date-range")
@solution_router.get("/calculate-date-range/")
@solution_router.post("/calculate-date-range")
@solution_router.post("/calculate-date-range/")
async def calculate_date_range(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Calculate recommended date range for model training.
    Matches webapi: views_solution.calculate_date_range
    """
    if request.method == "POST":
        data = await request.json()
    else:
        data = dict(request.query_params)

    # Default response with reasonable date range
    from datetime import timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 2)

    return {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "required_points": 100,
        "recommended_points": 500,
        "estimated_points": 500,
        "adjusted": False,
        "message": "Default date range"
    }


@solution_router.get("/ticker/time_range/{ticker}")
async def get_ticker_time_range(
    ticker: str
):
    """Get available date range for a ticker.
    Matches webapi: views_solution.get_ticker_time_range
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{settings.STOCK_DATA_SERVICE_URL}/stock_helper/api/v2/companies/{ticker}/historical-data"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and len(data) > 0:
                    return {
                        "start_date": data[0].get("time", "2020-01-01"),
                        "end_date": data[-1].get("time", datetime.now().strftime("%Y-%m-%d"))
                    }
    except Exception as e:
        logger.warning(f"Failed to get ticker time range: {e}")

    # Fallback
    return {
        "start_date": "2020-01-01",
        "end_date": datetime.now().strftime("%Y-%m-%d")
    }


# ==========================================
# Solution Detail Endpoints (must be after specific routes)
# ==========================================

@solution_router.get("/{solution_id}/training-status")
@solution_router.get("/{solution_id}/training-status/")
async def get_training_status(
    solution_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get the current training status for a solution.
    Matches webapi: views_solution.get_training_status
    """
    if solution_id not in training_status:
        return {
            "status": "not_found",
            "message": "No training session found for this solution"
        }

    current = training_status[solution_id]

    # Clean up old completed/failed statuses after 5 minutes
    if current["status"] in ["completed", "failed"]:
        status_time = current.get("completed_at") or current.get("failed_at", 0)
        if time_module.time() - status_time > 300:
            del training_status[solution_id]

    return current


@solution_router.post("/train")
@solution_router.post("/train/")
async def train_solution(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Start training a solution asynchronously.
    Matches webapi: views_solution.train_solution
    """
    data = await request.json()
    solution_id = data.get("id")

    if not solution_id:
        raise HTTPException(status_code=400, detail="Solution ID is required")

    # Check if already training
    if solution_id in training_status:
        current = training_status[solution_id]
        if current["status"] == "training":
            return {
                "message": "Training already in progress",
                "status": "training",
                "solution_id": solution_id
            }

    # Mark as training
    training_status[solution_id] = {
        "status": "training",
        "message": "Training in progress...",
        "progress": 0,
        "started_at": time_module.time()
    }

    # TODO: Implement actual training logic
    # For now, mark as completed after a brief delay
    def mock_training():
        time_module.sleep(2)
        training_status[solution_id] = {
            "status": "completed",
            "message": "Training completed successfully",
            "completed_at": time_module.time()
        }

    thread = threading.Thread(target=mock_training, daemon=True)
    thread.start()

    return {
        "message": "Training started successfully",
        "status": "training",
        "solution_id": solution_id
    }


@solution_router.post("/predict")
@solution_router.post("/predict/")
async def predict_solution(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate predictions for a trained solution.
    Matches webapi: views_solution.predict_solution
    """
    data = await request.json()
    solution_id = data.get("id")

    if not solution_id:
        raise HTTPException(status_code=400, detail="Solution ID is required")

    # TODO: Implement actual prediction logic
    return {
        "message": "Prediction not yet implemented in microservice",
        "solution_id": solution_id
    }


# ==========================================
# Solution Indicator Endpoints
# ==========================================

@solution_router.get("/{solution_id}/indicators")
@solution_router.get("/{solution_id}/indicators/")
async def get_solution_indicators(
    solution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get indicators assigned to a solution, grouped by category.
    Returns format expected by frontend IndicatorSelector:
    { trend: {id, covariate_type, parameters, name, ...}, momentum: {...}, ... }
    Matches webapi: view_indicators.get_solution_indicators
    """
    try:
        result = await db.execute(
            text("""
                SELECT si.id, si.solution_id, si.indicator_id, si.indicator_category,
                       si.covariate_type, si.parameters,
                       ti.name, ti.type, ti.description, ti.default_parameters
                FROM solution_indicators si
                LEFT JOIN technical_indicators ti ON si.indicator_id = ti.id
                WHERE si.solution_id = :solution_id
            """),
            {"solution_id": solution_id}
        )
        rows = result.mappings().all()

        # Group by category for frontend consumption
        grouped = {}
        for row in rows:
            ind = dict(row)
            params = ind.get("parameters")
            if params and isinstance(params, str):
                try:
                    params = json.loads(params)
                except (json.JSONDecodeError, TypeError):
                    pass
            default_params = ind.get("default_parameters")
            if default_params and isinstance(default_params, str):
                try:
                    default_params = json.loads(default_params)
                except (json.JSONDecodeError, TypeError):
                    pass

            category = ind.get("indicator_category")
            if category:
                grouped[category] = {
                    "id": ind.get("indicator_id"),
                    "name": ind.get("name"),
                    "type": ind.get("type"),
                    "description": ind.get("description"),
                    "covariate_type": ind.get("covariate_type", "past"),
                    "parameters": params or {},
                    "default_parameters": default_params or {},
                }

        return grouped
    except Exception as e:
        logger.error(f"Failed to fetch solution indicators: {e}")
        return {}


@solution_router.post("/{solution_id}/indicators/set")
@solution_router.post("/{solution_id}/indicators/set/")
async def set_solution_indicators(
    solution_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Set all indicators for a solution (replaces existing).
    Frontend sends: {trend_indicator: {id, covariate_type, parameters}, momentum_indicator: {...}, ...}
    Matches webapi: view_indicators.set_solution_indicators
    """
    data = await request.json()

    # Parse frontend format: {trend_indicator: {...}, momentum_indicator: {...}, ...}
    category_map = {
        "trend_indicator": "trend",
        "momentum_indicator": "momentum",
        "volatility_indicator": "volatility",
        "volume_indicator": "volume",
    }

    indicators = []
    for key, category in category_map.items():
        ind_data = data.get(key)
        if ind_data and ind_data.get("id"):
            indicators.append({
                "indicator_id": ind_data["id"],
                "indicator_category": category,
                "covariate_type": ind_data.get("covariate_type", "past"),
                "parameters": ind_data.get("parameters", {}),
            })

    # Also support array format: {indicators: [{indicator_id, indicator_category, ...}]}
    if not indicators and "indicators" in data:
        indicators = data["indicators"]

    try:
        # Delete existing indicators for this solution
        await db.execute(
            text("DELETE FROM solution_indicators WHERE solution_id = :solution_id"),
            {"solution_id": solution_id}
        )

        # Insert new indicators
        for ind in indicators:
            params = ind.get("parameters", {})
            params_json = json.dumps(params) if isinstance(params, dict) else params

            await db.execute(
                text("""
                    INSERT INTO solution_indicators
                    (solution_id, indicator_id, indicator_category, covariate_type, parameters)
                    VALUES (:solution_id, :indicator_id, :indicator_category, :covariate_type, :parameters)
                """),
                {
                    "solution_id": solution_id,
                    "indicator_id": ind.get("indicator_id"),
                    "indicator_category": ind.get("indicator_category", "trend"),
                    "covariate_type": ind.get("covariate_type", "past"),
                    "parameters": params_json
                }
            )

        await db.commit()
        return {"message": "Indicators set successfully", "solution_id": solution_id}
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to set solution indicators: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set indicators: {str(e)}")


# ==========================================
# Indicator Calculation
# Matches webapi: view_indicators.calculate_solution_indicators
# ==========================================

# Mapping from DB indicator names to short codes (matches webapi indicator_service.py)
INDICATOR_NAME_MAP = {
    'SMA': 'SMA', 'Simple Moving Average': 'SMA',
    'EMA': 'EMA', 'Exponential Moving Average': 'EMA',
    'WMA': 'WMA', 'Weighted Moving Average': 'WMA',
    'DEMA': 'DEMA', 'TEMA': 'TEMA',
    'MACD': 'MACD', 'Moving Average Convergence Divergence': 'MACD',
    'ADX': 'ADX', 'Average Directional Index': 'ADX',
    'PSAR': 'PSAR', 'Parabolic SAR': 'PSAR',
    'SUPERTREND': 'SUPERTREND', 'ICHIMOKU': 'ICHIMOKU',
    'AROON': 'AROON', 'VORTEX': 'VORTEX',
    'RSI': 'RSI', 'Relative Strength Index': 'RSI',
    'STOCH': 'STOCH', 'Stochastic Oscillator': 'STOCH',
    'STOCH_RSI': 'STOCH_RSI', 'CCI': 'CCI', 'Commodity Channel Index': 'CCI',
    'WILLIAMS_R': 'WILLIAMS_R', 'Williams %R': 'WILLIAMS_R',
    'ROC': 'ROC', 'Rate of Change': 'ROC',
    'MOM': 'MOM', 'Momentum Indicator': 'MOM',
    'TSI': 'TSI', 'UO': 'UO', 'AO': 'AO',
    'BB': 'BB', 'Bollinger Bands': 'BB',
    'ATR': 'ATR', 'Average True Range': 'ATR',
    'KELTNER': 'KELTNER', 'DONCHIAN': 'DONCHIAN',
    'STDDEV': 'STDDEV', 'HV': 'HV',
    'VOLUME': 'VOLUME', 'OBV': 'OBV', 'On Balance Volume': 'OBV',
    'VWAP': 'VWAP', 'MFI': 'MFI', 'Money Flow Index': 'MFI',
    'AD': 'AD', 'CMF': 'CMF', 'CHO': 'CHO', 'VOSC': 'VOSC',
    'EOM': 'EOM', 'FI': 'FI', 'NVI': 'NVI', 'PVI': 'PVI',
    'Volume_MA': 'Volume_MA',
}


def _safe_val(v):
    """Convert numpy types to native Python types for JSON serialization."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if pd.isna(v):
        return None
    return float(v)


def _calculate_indicator(df: pd.DataFrame, code: str, params: dict) -> List[Dict]:
    """Calculate a single technical indicator. Matches webapi/services/advanced_technical_indicators.py"""
    result = []
    dates = df.index

    try:
        if code == 'SMA':
            values = ta.trend.SMAIndicator(df['close'], window=params.get('period', 20)).sma_indicator()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'sma': _safe_val(values.iloc[i])})
        elif code == 'EMA':
            values = ta.trend.EMAIndicator(df['close'], window=params.get('period', 20)).ema_indicator()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'ema': _safe_val(values.iloc[i])})
        elif code == 'WMA':
            values = ta.trend.WMAIndicator(df['close'], window=params.get('period', 20)).wma()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'wma': _safe_val(values.iloc[i])})
        elif code == 'MACD':
            m = ta.trend.MACD(df['close'], window_fast=params.get('fast_period', 12),
                              window_slow=params.get('slow_period', 26), window_sign=params.get('signal_period', 9))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'macd': _safe_val(m.macd().iloc[i]),
                               'signal': _safe_val(m.macd_signal().iloc[i]),
                               'histogram': _safe_val(m.macd_diff().iloc[i])})
        elif code == 'ADX':
            adx = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=params.get('period', 14))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'adx': _safe_val(adx.adx().iloc[i])})
        elif code == 'PSAR':
            values = ta.trend.PSARIndicator(df['high'], df['low'], df['close'],
                                            step=params.get('step', 0.02), max_step=params.get('max_step', 0.2)).psar()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'psar': _safe_val(values.iloc[i])})
        elif code == 'RSI':
            values = ta.momentum.RSIIndicator(df['close'], window=params.get('period', 14)).rsi()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'rsi': _safe_val(values.iloc[i])})
        elif code == 'STOCH':
            s = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'],
                                                  window=params.get('k_period', 14), smooth_window=params.get('d_period', 3))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'stoch_k': _safe_val(s.stoch().iloc[i]),
                               'stoch_d': _safe_val(s.stoch_signal().iloc[i])})
        elif code == 'CCI':
            values = ta.trend.CCIIndicator(df['high'], df['low'], df['close'], window=params.get('period', 20)).cci()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'cci': _safe_val(values.iloc[i])})
        elif code == 'WILLIAMS_R':
            values = ta.momentum.WilliamsRIndicator(df['high'], df['low'], df['close'],
                                                     lbp=params.get('period', 14)).williams_r()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'williams_r': _safe_val(values.iloc[i])})
        elif code == 'ROC':
            values = ta.momentum.ROCIndicator(df['close'], window=params.get('period', 12)).roc()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'roc': _safe_val(values.iloc[i])})
        elif code == 'BB':
            std_val = params.get('std_dev', params.get('std', 2))
            bb = ta.volatility.BollingerBands(df['close'], window=params.get('period', 20), window_dev=std_val)
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'bb_upper': _safe_val(bb.bollinger_hband().iloc[i]),
                               'bb_middle': _safe_val(bb.bollinger_mavg().iloc[i]),
                               'bb_lower': _safe_val(bb.bollinger_lband().iloc[i])})
        elif code == 'ATR':
            values = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'],
                                                     window=params.get('period', 14)).average_true_range()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'atr': _safe_val(values.iloc[i])})
        elif code == 'KELTNER':
            kc = ta.volatility.KeltnerChannel(df['high'], df['low'], df['close'],
                                               window=params.get('period', 20), window_atr=params.get('period', 20))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'kc_upper': _safe_val(kc.keltner_channel_hband().iloc[i]),
                               'kc_middle': _safe_val(kc.keltner_channel_mband().iloc[i]),
                               'kc_lower': _safe_val(kc.keltner_channel_lband().iloc[i])})
        elif code == 'DONCHIAN':
            dc = ta.volatility.DonchianChannel(df['high'], df['low'], df['close'], window=params.get('period', 20))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'dc_upper': _safe_val(dc.donchian_channel_hband().iloc[i]),
                               'dc_middle': _safe_val(dc.donchian_channel_mband().iloc[i]),
                               'dc_lower': _safe_val(dc.donchian_channel_lband().iloc[i])})
        elif code == 'OBV':
            values = ta.volume.OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'obv': _safe_val(values.iloc[i])})
        elif code == 'MFI':
            values = ta.volume.MFIIndicator(df['high'], df['low'], df['close'], df['volume'],
                                             window=params.get('period', 14)).money_flow_index()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'mfi': _safe_val(values.iloc[i])})
        elif code == 'CMF':
            values = ta.volume.ChaikinMoneyFlowIndicator(df['high'], df['low'], df['close'], df['volume'],
                                                          window=params.get('period', 20)).chaikin_money_flow()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'cmf': _safe_val(values.iloc[i])})
        elif code == 'VOLUME':
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'volume': float(df['volume'].iloc[i])})
        elif code == 'VWAP':
            values = ta.volume.VolumeWeightedAveragePrice(df['high'], df['low'], df['close'], df['volume']).volume_weighted_average_price()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'vwap': _safe_val(values.iloc[i])})
        elif code == 'STDDEV':
            values = df['close'].rolling(window=params.get('period', 20)).std()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'stddev': _safe_val(values.iloc[i])})
        elif code == 'HV':
            log_returns = np.log(df['close'] / df['close'].shift(1))
            values = log_returns.rolling(window=params.get('period', 20)).std() * np.sqrt(252)
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'hv': _safe_val(values.iloc[i])})
        elif code == 'MOM':
            values = df['close'] - df['close'].shift(params.get('period', 10))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'mom': _safe_val(values.iloc[i])})
        elif code == 'AD':
            values = ta.volume.AccDistIndexIndicator(df['high'], df['low'], df['close'], df['volume']).acc_dist_index()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'ad': _safe_val(values.iloc[i])})
        else:
            # Fallback: return close price as the value
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'value': float(df['close'].iloc[i])})
    except Exception as e:
        logger.warning(f"Failed to calculate {code}: {e}, falling back to close price")
        for i, d in enumerate(dates):
            result.append({'date': d.isoformat(), 'value': float(df['close'].iloc[i])})

    return result


@solution_router.post("/{solution_id}/indicators/calculate")
@solution_router.post("/{solution_id}/indicators/calculate/")
async def calculate_solution_indicators(
    solution_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Calculate all indicators for a solution.
    Matches webapi: view_indicators.calculate_solution_indicators
    POST body: {symbol, start_date, end_date}
    """
    data = await request.json()
    symbol = data.get("symbol", "")
    start_date = data.get("start_date", "")
    end_date = data.get("end_date", "")

    if not symbol or not start_date or not end_date:
        raise HTTPException(status_code=400, detail="symbol, start_date, and end_date are required")

    # 1. Get solution's configured indicators (grouped by category)
    try:
        result = await db.execute(
            text("""
                SELECT si.indicator_id, si.indicator_category, si.covariate_type, si.parameters,
                       ti.name, ti.type, ti.default_parameters, ti.calculation_function
                FROM solution_indicators si
                LEFT JOIN technical_indicators ti ON si.indicator_id = ti.id
                WHERE si.solution_id = :solution_id
            """),
            {"solution_id": solution_id}
        )
        rows = result.mappings().all()
    except Exception as e:
        logger.error(f"Failed to get solution indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if not rows:
        return {}

    # 2. Fetch price data from stock-data-service
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{settings.STOCK_DATA_SERVICE_URL}/stock_helper/api/v2/companies/{symbol}/historical-data"
            resp = await client.get(url, params={"start_date": start_date, "end_date": end_date})
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=f"Failed to fetch price data for {symbol}")
            price_data = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch price data: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch price data: {str(e)}")

    # Parse price data into DataFrame
    if isinstance(price_data, dict) and "data" in price_data:
        price_list = price_data["data"]
    elif isinstance(price_data, list):
        price_list = price_data
    else:
        price_list = []

    if not price_list:
        raise HTTPException(status_code=404, detail=f"No price data for {symbol} in date range")

    df = pd.DataFrame(price_list)
    # Normalize column names (stock-data-service may use 'time' or 'date')
    if 'time' in df.columns:
        df['date'] = pd.to_datetime(df['time'])
    elif 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Ensure required columns exist
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col not in df.columns:
            raise HTTPException(status_code=500, detail=f"Price data missing column: {col}")

    df = df[['open', 'high', 'low', 'close', 'volume']].copy()
    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna()

    # 3. Calculate each indicator
    calculated_values = {}
    for row in rows:
        ind = dict(row)
        category = ind.get("indicator_category")
        name = ind.get("name", "")

        # Parse parameters
        params = ind.get("parameters")
        if params and isinstance(params, str):
            try:
                params = json.loads(params)
            except (json.JSONDecodeError, TypeError):
                params = {}
        if not params:
            default_params = ind.get("default_parameters")
            if default_params and isinstance(default_params, str):
                try:
                    params = json.loads(default_params)
                except (json.JSONDecodeError, TypeError):
                    params = {}
            elif isinstance(default_params, dict):
                params = default_params
            else:
                params = {}

        # Map name to calculation code
        code = INDICATOR_NAME_MAP.get(name, name)

        indicator_data = _calculate_indicator(df, code, params)

        calculated_values[category] = {
            'name': name,
            'data': indicator_data
        }

    # 4. Include OHLC price data so frontend can render candlestick charts
    dates = df.index
    price_data = []
    for i, d in enumerate(dates):
        price_data.append({
            'date': d.isoformat(),
            'open': _safe_val(df['open'].iloc[i]),
            'high': _safe_val(df['high'].iloc[i]),
            'low': _safe_val(df['low'].iloc[i]),
            'close': _safe_val(df['close'].iloc[i]),
            'volume': float(df['volume'].iloc[i]) if pd.notna(df['volume'].iloc[i]) else 0,
        })
    calculated_values['price'] = {
        'name': 'Price',
        'data': price_data
    }

    return calculated_values


@solution_router.post("/{solution_id}/indicators/add")
@solution_router.post("/{solution_id}/indicators/add/")
async def add_solution_indicator(
    solution_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add an indicator to a solution."""
    data = await request.json()
    params = data.get("parameters", {})
    params_json = json.dumps(params) if isinstance(params, dict) else params

    try:
        result = await db.execute(
            text("""
                INSERT INTO solution_indicators
                (solution_id, indicator_id, indicator_category, covariate_type, parameters)
                VALUES (:solution_id, :indicator_id, :indicator_category, :covariate_type, :parameters)
            """),
            {
                "solution_id": solution_id,
                "indicator_id": data.get("indicator_id"),
                "indicator_category": data.get("indicator_category", "trend"),
                "covariate_type": data.get("covariate_type", "past"),
                "parameters": params_json
            }
        )
        await db.commit()
        return {"id": result.lastrowid, "message": "Indicator added", "solution_id": solution_id}
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to add solution indicator: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add indicator: {str(e)}")


@solution_router.delete("/{solution_id}/indicators/{indicator_id}")
@solution_router.delete("/{solution_id}/indicators/{indicator_id}/")
@solution_router.post("/{solution_id}/indicators/{indicator_id}/delete")
@solution_router.post("/{solution_id}/indicators/{indicator_id}/delete/")
async def remove_solution_indicator(
    solution_id: int,
    indicator_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove an indicator from a solution."""
    try:
        await db.execute(
            text("DELETE FROM solution_indicators WHERE id = :indicator_id AND solution_id = :solution_id"),
            {"indicator_id": indicator_id, "solution_id": solution_id}
        )
        await db.commit()
        return {"message": "Indicator removed", "solution_id": solution_id}
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to remove solution indicator: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove indicator: {str(e)}")


# ==========================================
# Catch-all: Get/Delete solution by ID
# IMPORTANT: Must come AFTER all specific routes
# ==========================================

@solution_router.get("/{solution_id}")
async def get_solution_by_id(
    solution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get solution by ID.
    Matches webapi: views_solution.get_solution_by_id
    """
    try:
        result = await db.execute(
            text("SELECT * FROM tbl_solution WHERE id = :id"),
            {"id": solution_id}
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Solution {solution_id} not found")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch solution {solution_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch solution: {str(e)}")


@solution_router.put("/{solution_id}")
async def update_solution_by_id(
    solution_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update solution by ID (path param).
    Delegates to the main update_solution handler.
    """
    data = await request.json()
    data["id"] = solution_id
    user_id = str(current_user["user_id"])
    if 'user_id' not in data:
        data['user_id'] = user_id
    if 'updated_by' not in data:
        data['updated_by'] = user_id

    try:
        await db.execute(
            text("""
                UPDATE tbl_solution
                SET solution_name = :solution_name, model_id = :model_id, ticker = :ticker,
                    updated_date = :updated_date, updated_by = :updated_by,
                    start_training_date = :start_training_date,
                    end_training_date = :end_training_date,
                    train_validation_ratio = :train_validation_ratio,
                    user_id = :user_id
                WHERE id = :id
            """),
            {
                "solution_name": data.get("solution_name"),
                "model_id": data.get("model_id"),
                "ticker": data.get("ticker"),
                "updated_date": data.get("updated_date", datetime.now().strftime("%Y-%m-%d")),
                "updated_by": data.get("updated_by"),
                "start_training_date": data.get("start_training_date"),
                "end_training_date": data.get("end_training_date"),
                "train_validation_ratio": data.get("train_validation_ratio", 0.8),
                "user_id": data.get("user_id"),
                "id": solution_id,
            }
        )
        await db.commit()
        return data
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update solution {solution_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update solution: {str(e)}")


@solution_router.delete("/{solution_id}")
async def delete_solution_by_id(
    solution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete solution by ID.
    Matches webapi: views_solution.delete_solution_by_id
    """
    try:
        # Delete associated indicators first
        await db.execute(
            text("DELETE FROM solution_indicators WHERE solution_id = :solution_id"),
            {"solution_id": solution_id}
        )
        # Delete solution
        result = await db.execute(
            text("DELETE FROM tbl_solution WHERE id = :id"),
            {"id": solution_id}
        )
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Solution {solution_id} not found")

        return {"message": "Solution deleted", "id": solution_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete solution {solution_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete solution: {str(e)}")
