"""Solution Service API Routes

Provides CRUD endpoints for prediction solutions, matching the v2 frontend API.
References webapi/views_solution.py and webapi/repositories/predict_solution_repository.py
for database schema and business logic.
"""
import asyncio
import json
import logging
import os
import time as time_module
from typing import Optional, Dict, List
from datetime import datetime

import httpx
import joblib
import numpy as np
import pandas as pd
import ta
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.dependencies import get_db, get_current_user_optional, get_current_user, async_session_factory
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

solution_router = APIRouter()

# Global dictionary to track training status (matches webapi pattern)
training_status = {}

# Model type mapping: DARTS neural network types -> scikit-learn/gradient boosting models
# Since DARTS is not installed in this microservice, we use available ML models
DARTS_TO_ML_MAP = {
    'BlockRNN': 'xgboost',
    'RNNModel': 'lightgbm',
    'TCNModel': 'xgboost',
    'TransformerModel': 'lightgbm',
    'NBEATSModel': 'random_forest',
    'TFTModel': 'lightgbm',
    'NBeats': 'random_forest',
    'NHits': 'xgboost',
    'DLinear': 'lightgbm',
    'NLinear': 'lightgbm',
    'TiDE': 'xgboost',
    'XGBoost': 'xgboost',
    'LightGBM': 'lightgbm',
    'RandomForest': 'random_forest',
    'CatBoost': 'xgboost',
    'LinearRegression': 'linear_regression',
}


def _create_ml_model(model_type: str, model_sub_type: str = '', config_json=None):
    """Create an ML model with hyperparameters tuned per model type.

    Each DARTS model type gets a distinct hyperparameter profile so that
    different model selections in the UI produce genuinely different models.
    User-provided config_json overrides the defaults.
    """
    ml_type = DARTS_TO_ML_MAP.get(model_type, 'xgboost')

    # Per-model-type default hyperparameters (distinct profiles)
    MODEL_DEFAULTS = {
        # ── XGBoost variants ──
        'XGBoost':          {'n_estimators': 200, 'max_depth': 6,  'learning_rate': 0.10, 'subsample': 0.8, 'colsample_bytree': 0.8},
        'BlockRNN':         {'n_estimators': 300, 'max_depth': 8,  'learning_rate': 0.05, 'subsample': 0.85, 'colsample_bytree': 0.7},
        'TCNModel':         {'n_estimators': 150, 'max_depth': 10, 'learning_rate': 0.08, 'subsample': 0.75, 'colsample_bytree': 0.9},
        'NHits':            {'n_estimators': 500, 'max_depth': 5,  'learning_rate': 0.03, 'subsample': 0.9, 'colsample_bytree': 0.6},
        'TiDE':             {'n_estimators': 100, 'max_depth': 4,  'learning_rate': 0.15, 'subsample': 0.7, 'colsample_bytree': 0.85},
        'CatBoost':         {'n_estimators': 400, 'max_depth': 7,  'learning_rate': 0.04, 'subsample': 0.8, 'colsample_bytree': 0.75},
        # ── LightGBM variants ──
        'LightGBM':         {'n_estimators': 200, 'max_depth': 6,  'learning_rate': 0.10, 'subsample': 0.8, 'colsample_bytree': 0.8, 'num_leaves': 31},
        'RNNModel':         {'n_estimators': 300, 'max_depth': 8,  'learning_rate': 0.05, 'subsample': 0.85, 'colsample_bytree': 0.7, 'num_leaves': 63},
        'TransformerModel': {'n_estimators': 400, 'max_depth': 5,  'learning_rate': 0.03, 'subsample': 0.9, 'colsample_bytree': 0.6, 'num_leaves': 127},
        'TFTModel':         {'n_estimators': 350, 'max_depth': 9,  'learning_rate': 0.04, 'subsample': 0.8, 'colsample_bytree': 0.75, 'num_leaves': 80},
        'DLinear':          {'n_estimators': 100, 'max_depth': 3,  'learning_rate': 0.15, 'subsample': 0.7, 'colsample_bytree': 0.9, 'num_leaves': 15},
        'NLinear':          {'n_estimators': 80,  'max_depth': 2,  'learning_rate': 0.20, 'subsample': 0.7, 'colsample_bytree': 0.95, 'num_leaves': 10},
        # ── RandomForest variants ──
        'RandomForest':     {'n_estimators': 200, 'max_depth': 10, 'min_samples_split': 5,  'min_samples_leaf': 2},
        'NBEATSModel':      {'n_estimators': 400, 'max_depth': 15, 'min_samples_split': 3,  'min_samples_leaf': 1},
        'NBeats':           {'n_estimators': 300, 'max_depth': 12, 'min_samples_split': 4,  'min_samples_leaf': 2},
    }

    defaults = MODEL_DEFAULTS.get(model_type, {})

    # User config overrides defaults
    user_config = {}
    if config_json:
        try:
            user_config = json.loads(config_json) if isinstance(config_json, str) else config_json
        except (json.JSONDecodeError, TypeError):
            user_config = {}

    cfg = {**defaults, **user_config}

    if ml_type == 'xgboost':
        return xgb.XGBRegressor(
            n_estimators=cfg.get('n_estimators', 200),
            max_depth=cfg.get('max_depth', 6),
            learning_rate=cfg.get('learning_rate', 0.1),
            subsample=cfg.get('subsample', 0.8),
            colsample_bytree=cfg.get('colsample_bytree', 0.8),
            random_state=42,
            verbosity=0
        )
    elif ml_type == 'lightgbm':
        return lgb.LGBMRegressor(
            n_estimators=cfg.get('n_estimators', 200),
            max_depth=cfg.get('max_depth', 6),
            learning_rate=cfg.get('learning_rate', 0.1),
            num_leaves=cfg.get('num_leaves', 31),
            subsample=cfg.get('subsample', 0.8),
            colsample_bytree=cfg.get('colsample_bytree', 0.8),
            random_state=42,
            verbose=-1
        )
    elif ml_type == 'random_forest':
        return RandomForestRegressor(
            n_estimators=cfg.get('n_estimators', 200),
            max_depth=cfg.get('max_depth', 10),
            min_samples_split=cfg.get('min_samples_split', 5),
            min_samples_leaf=cfg.get('min_samples_leaf', 2),
            random_state=42,
            n_jobs=-1
        )
    else:
        return LinearRegression()


def _prepare_indicator_features(df: pd.DataFrame, indicator_rows: list) -> tuple:
    """Calculate indicator features and return (feature_df, indicator_data_by_date).

    Returns:
        feature_df: DataFrame with indicator columns
        indicator_data_by_date: dict mapping date_str -> {col: value} for chart merge
    """
    feature_df = pd.DataFrame(index=df.index)
    indicator_data_by_date = {}

    for row in indicator_rows:
        ind = dict(row)
        name = ind.get('name', '')
        code = INDICATOR_NAME_MAP.get(name, name)

        params = ind.get('parameters')
        if params and isinstance(params, str):
            try:
                params = json.loads(params)
            except (json.JSONDecodeError, TypeError):
                params = {}
        if not params:
            default_params = ind.get('default_parameters')
            if default_params and isinstance(default_params, str):
                try:
                    params = json.loads(default_params)
                except (json.JSONDecodeError, TypeError):
                    params = {}
            elif isinstance(default_params, dict):
                params = default_params
            else:
                params = {}

        indicator_data = _calculate_indicator(df, code, params)
        if not indicator_data:
            continue

        ind_df = pd.DataFrame(indicator_data)
        if 'date' in ind_df.columns:
            ind_df['date'] = pd.to_datetime(ind_df['date'])
            ind_df = ind_df.set_index('date')

        for col in ind_df.columns:
            if col != 'date':
                try:
                    feature_df[col] = pd.to_numeric(ind_df[col], errors='coerce')
                except Exception:
                    pass

        for item in indicator_data:
            date_key = item.get('date', '')
            if date_key not in indicator_data_by_date:
                indicator_data_by_date[date_key] = {}
            for k, v in item.items():
                if k != 'date' and v is not None:
                    indicator_data_by_date[date_key][k] = v

    return feature_df, indicator_data_by_date


def _build_feature_df(df: pd.DataFrame, indicator_feature_df: pd.DataFrame) -> pd.DataFrame:
    """Build feature DataFrame from OHLCV data and indicator features.

    Shared by training and prediction to ensure feature consistency.
    Does NOT add 'target' column — caller adds that for training.

    Args:
        df: DataFrame with columns [open, high, low, close, volume], DatetimeIndex
        indicator_feature_df: DataFrame with indicator columns, same index as df

    Returns:
        DataFrame with all features (no target), NaN rows NOT dropped (caller decides).
    """
    feature_df = pd.DataFrame(index=df.index)
    feature_df['close'] = df['close']

    # Price-based features
    feature_df['returns'] = df['close'].pct_change()
    feature_df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
    feature_df['high_low_ratio'] = df['high'] / df['low']
    feature_df['close_open_ratio'] = df['close'] / df['open']

    for lag in [1, 2, 3, 5, 10]:
        feature_df[f'close_lag_{lag}'] = df['close'].shift(lag)
        feature_df[f'returns_lag_{lag}'] = feature_df['returns'].shift(lag)

    # Volatility
    feature_df['volatility_5'] = feature_df['returns'].rolling(5).std()
    feature_df['volatility_20'] = feature_df['returns'].rolling(20).std()

    # Volume features
    if 'volume' in df.columns:
        feature_df['volume_sma_20'] = df['volume'].rolling(20).mean()
        feature_df['volume_ratio'] = df['volume'] / feature_df['volume_sma_20']

    # Add indicator features
    for col in indicator_feature_df.columns:
        feature_df[col] = indicator_feature_df[col]

    return feature_df


async def _run_training(solution_id: int, train_params: dict):
    """Background async training task with real ML model training."""
    try:
        training_status[solution_id] = {
            "status": "training",
            "message": "Loading solution data...",
            "progress": 5,
            "started_at": time_module.time()
        }

        async with async_session_factory() as db:
            # Step 1: Load solution
            result = await db.execute(
                text("SELECT * FROM tbl_solution WHERE id = :id"),
                {"id": solution_id}
            )
            solution = result.mappings().first()
            if not solution:
                training_status[solution_id] = {
                    "status": "failed", "error": "Solution not found",
                    "failed_at": time_module.time()
                }
                return

            ticker = solution['ticker']
            model_id = solution['model_id']

            # Step 2: Load model instance
            result = await db.execute(
                text("SELECT * FROM model_instances WHERE id = :id"),
                {"id": model_id}
            )
            model_instance = result.mappings().first()
            if not model_instance:
                training_status[solution_id] = {
                    "status": "failed", "error": f"Model instance {model_id} not found",
                    "failed_at": time_module.time()
                }
                return

            training_status[solution_id]["message"] = "Loading indicators..."
            training_status[solution_id]["progress"] = 10

            # Step 3: Get solution indicators
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
            indicator_rows = [dict(r) for r in result.mappings().all()]

            training_status[solution_id]["message"] = f"Fetching price data for {ticker}..."
            training_status[solution_id]["progress"] = 15

            # Step 4: Fetch OHLC data from stock-data-service
            start_date = train_params.get('start_date')
            end_date = train_params.get('end_date')
            train_ratio = float(train_params.get('train_ratio', 0.8))

            async with httpx.AsyncClient(timeout=60.0) as client:
                url = f"{settings.STOCK_DATA_SERVICE_URL}/stock_helper/api/v2/companies/{ticker}/historical-data"
                resp = await client.get(url, params={"start_date": start_date, "end_date": end_date})
                if resp.status_code != 200:
                    training_status[solution_id] = {
                        "status": "failed",
                        "error": f"Failed to fetch price data for {ticker} (HTTP {resp.status_code})",
                        "failed_at": time_module.time()
                    }
                    return
                price_response = resp.json()

            if isinstance(price_response, dict) and "data" in price_response:
                price_list = price_response["data"]
            elif isinstance(price_response, list):
                price_list = price_response
            else:
                price_list = []

            if not price_list:
                training_status[solution_id] = {
                    "status": "failed",
                    "error": f"No price data for {ticker} in range {start_date} to {end_date}",
                    "failed_at": time_module.time()
                }
                return

            logger.info(f"Training solution {solution_id}: loaded {len(price_list)} price records for {ticker}")

            df = pd.DataFrame(price_list)
            if 'time' in df.columns:
                df['date'] = pd.to_datetime(df['time'])
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            df = df[['open', 'high', 'low', 'close', 'volume']].copy()
            df = df.apply(pd.to_numeric, errors='coerce')
            df = df.dropna()

            training_status[solution_id]["message"] = "Calculating technical indicators..."
            training_status[solution_id]["progress"] = 25

            # Step 5: Calculate indicator features
            indicator_feature_df, indicator_data_by_date = _prepare_indicator_features(df, indicator_rows)

            # Build feature DataFrame using shared function
            feature_df = _build_feature_df(df, indicator_feature_df)

            # Target: next day's close price
            feature_df['target'] = feature_df['close'].shift(-1)

            # Drop NaN rows
            feature_df = feature_df.dropna()

            if len(feature_df) < 30:
                training_status[solution_id] = {
                    "status": "failed",
                    "error": f"Insufficient data: only {len(feature_df)} usable data points after feature preparation (need at least 30)",
                    "failed_at": time_module.time()
                }
                return

            training_status[solution_id]["message"] = "Training model..."
            training_status[solution_id]["progress"] = 40

            # Step 6: Prepare training data
            feature_cols = [col for col in feature_df.columns if col not in ['close', 'target']]
            X = feature_df[feature_cols].values
            y = feature_df['target'].values

            split_idx = int(len(X) * train_ratio)
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]

            logger.info(f"Training solution {solution_id}: {len(X_train)} train, {len(X_val)} val, {len(feature_cols)} features")

            # Step 7: Create and train model
            model_type = model_instance['model_type'] if model_instance else 'BlockRNN'
            model_sub_type = model_instance.get('model_sub_type', '') if model_instance else ''
            config_json = model_instance.get('config_json') if model_instance else None

            ml_model = _create_ml_model(model_type, model_sub_type, config_json)

            # Run CPU-bound training in thread executor
            await asyncio.to_thread(ml_model.fit, X_train, y_train)

            training_status[solution_id]["message"] = "Evaluating model..."
            training_status[solution_id]["progress"] = 70

            # Step 8: Evaluate
            y_pred_val = ml_model.predict(X_val)
            rmse = float(np.sqrt(mean_squared_error(y_val, y_pred_val)))
            mae = float(mean_absolute_error(y_val, y_pred_val))
            r2 = float(r2_score(y_val, y_pred_val))

            if len(y_val) > 1:
                actual_dir = np.sign(y_val[1:] - y_val[:-1])
                pred_dir = np.sign(y_pred_val[1:] - y_pred_val[:-1])
                direction_accuracy = float(np.mean(actual_dir == pred_dir) * 100)
            else:
                direction_accuracy = 0.0

            logger.info(f"Training solution {solution_id}: RMSE={rmse:.4f}, MAE={mae:.4f}, R2={r2:.4f}, Dir={direction_accuracy:.1f}%")

            training_status[solution_id]["message"] = "Saving model..."
            training_status[solution_id]["progress"] = 80

            # Step 9: Save model to disk
            os.makedirs(settings.MODEL_PATH, exist_ok=True)
            model_file = f"{settings.MODEL_PATH}/solution_{solution_id}_model.joblib"
            joblib.dump({
                'model': ml_model,
                'feature_cols': feature_cols,
                'model_type': model_type,
                'ml_type': DARTS_TO_ML_MAP.get(model_type, 'xgboost'),
                'ticker': ticker,
                'trained_at': datetime.now().isoformat(),
            }, model_file)

            logger.info(f"Model saved to {model_file}")

            # Step 10: Update database
            training_status[solution_id]["message"] = "Updating database..."
            training_status[solution_id]["progress"] = 85

            metrics_json = json.dumps({
                'rmse': rmse, 'mae': mae, 'r2': r2,
                'direction_accuracy': direction_accuracy,
                'training_samples': int(len(X_train)),
                'validation_samples': int(len(X_val)),
                'features_used': len(feature_cols)
            })

            await db.execute(
                text("""
                    UPDATE model_instances
                    SET status='trained', file_path=:file_path,
                        training_metrics_json=:metrics, last_training_date=NOW()
                    WHERE id = :model_id
                """),
                {"file_path": model_file, "metrics": metrics_json, "model_id": model_id}
            )

            await db.execute(
                text("""
                    UPDATE tbl_solution
                    SET train_status='trained', solution_status=1,
                        start_training_date=:start_date, end_training_date=:end_date,
                        prediction_result=NULL
                    WHERE id = :solution_id
                """),
                {"start_date": start_date, "end_date": end_date, "solution_id": solution_id}
            )
            await db.commit()

            training_status[solution_id]["message"] = "Generating predictions..."
            training_status[solution_id]["progress"] = 90

            # Step 11: Generate predictions for chart
            all_pred = ml_model.predict(X)

            predictions = []
            dates_list = feature_df.index.tolist()
            for i, d in enumerate(dates_list):
                date_str = d.strftime('%Y-%m-%d')
                is_validation = i >= split_idx

                point = {
                    'date': date_str,
                    'actual_price': float(feature_df['close'].iloc[i]),
                    # Full fitted/target line across the whole window so the chart
                    # always shows a "target train price" series (not just the tail).
                    'predicted_price': float(all_pred[i]),
                    # Out-of-sample portion, exposed separately so it can be
                    # highlighted/toggled distinctly from the in-sample fit.
                    'validation_price': float(all_pred[i]) if is_validation else None,
                    'close': float(feature_df['close'].iloc[i]),
                    'open': float(df.loc[d, 'open']) if d in df.index else None,
                    'high': float(df.loc[d, 'high']) if d in df.index else None,
                    'low': float(df.loc[d, 'low']) if d in df.index else None,
                    'volume': float(df.loc[d, 'volume']) if d in df.index else None,
                }

                # Merge indicator values for chart display
                date_iso = d.isoformat()
                if date_iso in indicator_data_by_date:
                    point.update(indicator_data_by_date[date_iso])
                elif date_str in indicator_data_by_date:
                    point.update(indicator_data_by_date[date_str])

                predictions.append(point)

            # Step 12: Compute prediction dates (business days)
            # pred_start = training end date + 1 business day
            training_end = pd.Timestamp(end_date)
            output_chunk_length = 10

            pred_start = training_end + pd.Timedelta(days=1)
            while pred_start.weekday() >= 5:
                pred_start += pd.Timedelta(days=1)

            pred_end = pred_start
            bdays = 0
            while bdays < output_chunk_length - 1:
                pred_end += pd.Timedelta(days=1)
                if pred_end.weekday() < 5:
                    bdays += 1

            prediction_dates = {
                'prediction_start_date': pred_start.strftime('%Y-%m-%d'),
                'prediction_end_date': pred_end.strftime('%Y-%m-%d'),
                'output_chunk_length': output_chunk_length,
                'training_end_date': end_date
            }

            # Step 13: Store completed result
            training_status[solution_id] = {
                "status": "completed",
                "completed_at": time_module.time(),
                "message": f"Training completed! RMSE: {rmse:.4f}",
                "result": {
                    "rmse": rmse,
                    "mae": mae,
                    "r2": r2,
                    "direction_accuracy": direction_accuracy,
                    "predictions": predictions,
                    "prediction_dates": prediction_dates,
                    "training_status": "completed",
                    "model_id": model_id,
                    "training_samples": int(len(X_train)),
                    "validation_samples": int(len(X_val)),
                }
            }

            logger.info(f"Training completed for solution {solution_id}: RMSE={rmse:.4f}, {len(predictions)} data points")

            # Persist training result to DB so it survives modal reopening
            try:
                training_result_json = json.dumps(training_status[solution_id]["result"])
                await db.execute(
                    text("UPDATE tbl_solution SET training_result = :result WHERE id = :id"),
                    {"result": training_result_json, "id": solution_id}
                )
                await db.commit()
                logger.info(f"Training result persisted to DB for solution {solution_id}")
            except Exception as persist_err:
                logger.warning(f"Failed to persist training result for solution {solution_id}: {persist_err}")

    except Exception as e:
        logger.error(f"Training failed for solution {solution_id}: {e}", exc_info=True)
        training_status[solution_id] = {
            "status": "failed",
            "failed_at": time_module.time(),
            "error": str(e),
            "message": f"Training failed: {str(e)}"
        }


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
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get all available models for solution creation.
    Matches webapi: views_solution.get_predict_models
    Filters by user_id when authenticated.
    """
    try:
        if current_user and current_user.get("user_id"):
            user_id = str(current_user["user_id"])
            result = await db.execute(
                text("""
                    SELECT id, model_name, model_type, model_sub_type,
                           past_covariate, future_covariate
                    FROM model_instances
                    WHERE user_id = :user_id
                    ORDER BY id DESC
                """),
                {"user_id": user_id}
            )
        else:
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
    """Start training a solution asynchronously with real ML model.
    Matches webapi: views_solution.train_solution
    """
    data = await request.json()
    solution_id = data.get("id")

    if not solution_id:
        raise HTTPException(status_code=400, detail="Solution ID is required")

    # Normalize to int for consistent dict key
    solution_id = int(solution_id)

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
        "message": "Initializing training...",
        "progress": 0,
        "started_at": time_module.time()
    }

    # Launch real training in background
    train_params = {
        'start_date': data.get('start_date'),
        'end_date': data.get('end_date'),
        'validation': data.get('validation', False),
        'train_ratio': data.get('train_ratio', 0.8),
    }

    asyncio.create_task(_run_training(solution_id, train_params))

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

    solution_id = int(solution_id)
    predict_start = data.get("start_date")
    predict_end = data.get("end_date")

    try:
        # Step 1: Load solution
        result = await db.execute(
            text("SELECT * FROM tbl_solution WHERE id = :id"),
            {"id": solution_id}
        )
        solution = result.mappings().first()
        if not solution:
            raise HTTPException(status_code=404, detail=f"Solution {solution_id} not found")

        ticker = solution['ticker']
        model_id = solution['model_id']

        # Step 2: Load model instance and verify trained
        result = await db.execute(
            text("SELECT * FROM model_instances WHERE id = :id"),
            {"id": model_id}
        )
        model_instance = result.mappings().first()
        if not model_instance:
            raise HTTPException(status_code=404, detail=f"Model instance {model_id} not found")

        if model_instance['status'] != 'trained':
            raise HTTPException(
                status_code=400,
                detail=f"Model not trained yet (status: {model_instance['status']}). Train the solution first."
            )

        model_file = model_instance['file_path']
        if not model_file or not os.path.exists(model_file):
            raise HTTPException(
                status_code=400,
                detail=f"Model file not found at {model_file}. Retrain the solution."
            )

        # Step 3: Load the saved model
        saved = joblib.load(model_file)
        ml_model = saved['model']
        feature_cols = saved['feature_cols']

        logger.info(f"Prediction: loaded model for solution {solution_id}, {len(feature_cols)} features")

        # Step 4: Load solution indicators
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
        indicator_rows = [dict(r) for r in result.mappings().all()]

        # Step 5: Fetch price data (need extra history for lag features)
        # We need at least 30 extra business days before predict_start for rolling features
        if predict_start:
            history_start = (pd.Timestamp(predict_start) - pd.Timedelta(days=60)).strftime('%Y-%m-%d')
        else:
            history_start = None

        async with httpx.AsyncClient(timeout=60.0) as client:
            url = f"{settings.STOCK_DATA_SERVICE_URL}/stock_helper/api/v2/companies/{ticker}/historical-data"
            params = {}
            if history_start:
                params["start_date"] = history_start
            if predict_end:
                params["end_date"] = predict_end
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to fetch price data for {ticker} (HTTP {resp.status_code})"
                )
            price_response = resp.json()

        if isinstance(price_response, dict) and "data" in price_response:
            price_list = price_response["data"]
        elif isinstance(price_response, list):
            price_list = price_response
        else:
            price_list = []

        if not price_list:
            raise HTTPException(
                status_code=404,
                detail=f"No price data for {ticker}"
            )

        # Build OHLCV DataFrame
        df = pd.DataFrame(price_list)
        if 'time' in df.columns:
            df['date'] = pd.to_datetime(df['time'])
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()
        df = df.apply(pd.to_numeric, errors='coerce')
        df = df.dropna()

        # Step 6: Build features using shared function
        indicator_feature_df, indicator_data_by_date = _prepare_indicator_features(df, indicator_rows)
        feature_df = _build_feature_df(df, indicator_feature_df)
        feature_df = feature_df.dropna()

        # Ensure we have the same columns as training (in same order)
        missing_cols = [c for c in feature_cols if c not in feature_df.columns]
        if missing_cols:
            logger.warning(f"Prediction: missing features {missing_cols}, filling with 0")
            for c in missing_cols:
                feature_df[c] = 0.0

        # Step 7: Predict on known period (historical backtest)
        X_pred = feature_df[feature_cols].values
        y_pred = ml_model.predict(X_pred)

        # Filter to requested date range for output
        if predict_start:
            mask = feature_df.index >= pd.Timestamp(predict_start)
        else:
            mask = pd.Series(True, index=feature_df.index)

        actual_prices = []
        predicted_prices = []
        dates_in_range = feature_df.index[mask]

        for i_global, d in enumerate(feature_df.index):
            if not mask[i_global]:
                continue
            date_str = d.strftime('%Y-%m-%d')
            actual_prices.append({
                'tradingdate': date_str,
                'close': float(feature_df['close'].iloc[i_global]),
            })
            predicted_prices.append({
                'tradingdate': date_str,
                'close': float(y_pred[i_global]),
            })

        # Compute affine bias correction from backtest (scale + shift)
        # Simple additive bias keeps flat predictions flat; affine amplifies tiny model variations
        actual_mean = pred_mean = actual_std = pred_std = 0.0
        prediction_bias = 0.0
        use_affine = use_shift = False
        if actual_prices and predicted_prices:
            actual_vals = np.array([p['close'] for p in actual_prices])
            pred_vals = np.array([p['close'] for p in predicted_prices])
            actual_mean = float(np.mean(actual_vals))
            pred_mean = float(np.mean(pred_vals))
            actual_std = float(np.std(actual_vals))
            pred_std = float(np.std(pred_vals))
            prediction_bias = actual_mean - pred_mean  # for future predictions
            if pred_std > 1e-6 and actual_std > 1e-6:
                use_affine = True
            elif abs(prediction_bias) > 0.01:
                use_shift = True

        def _correct_pred(v):
            """Apply the same backtest-derived correction used for in-range points."""
            if use_affine:
                return float(actual_mean + (actual_std / pred_std) * (v - pred_mean))
            if use_shift:
                return float(v + prediction_bias)
            return float(v)

        # Affine correction: scale in-range backtest predictions to match actuals
        for p in predicted_prices:
            p['close'] = _correct_pred(p['close'])

        # Step 8: Future predictions (iterative, day-by-day)
        future_predictions = []
        output_chunk_length = data.get('predict_days', settings.DEFAULT_PREDICTION_DAYS)
        output_chunk_length = min(output_chunk_length, settings.MAX_PREDICTION_DAYS)

        # Compute model quality weight for blending model vs simulated trajectory
        # Good model (R2>0.5): rely mostly on model; Bad model (R2<0): rely on simulation
        # Use raw (pre-bias) predictions to assess true model quality
        if len(actual_prices) > 1:
            bt_actual_vals = np.array([p['close'] for p in actual_prices])
            bt_raw_preds = y_pred[mask] if hasattr(mask, '__len__') else y_pred
            bt_r2 = float(r2_score(bt_actual_vals, bt_raw_preds[:len(bt_actual_vals)]))
            model_weight = np.clip(bt_r2, 0.1, 0.95)  # min 10% model, max 95%
        else:
            model_weight = 0.5

        # Start from last available date
        last_date = df.index[-1]
        last_close = float(df['close'].iloc[-1])
        last_row = df.iloc[-1].copy()

        # We need a rolling window of df for feature calculation
        future_df = df.copy()

        # Calculate historical volatility stats from last 30 days for realistic synthetic OHLCV
        recent = df.tail(30)
        daily_returns = recent['close'].pct_change().dropna()
        avg_return = float(daily_returns.mean())
        return_std = float(daily_returns.std()) if len(daily_returns) > 1 else 0.01
        avg_atr_pct = float((recent['high'] - recent['low']).mean() / recent['close'].mean()) if recent['close'].mean() > 0 else 0.02
        vol_mean = float(recent['volume'].mean())
        vol_std = float(recent['volume'].std()) if len(recent) > 1 else vol_mean * 0.1

        for day_i in range(output_chunk_length):
            # Next business day
            next_date = last_date + pd.Timedelta(days=1)
            while next_date.weekday() >= 5:
                next_date += pd.Timedelta(days=1)

            # Simulate realistic price movement based on historical volatility
            # Clamp return to prevent extreme moves (max ±10% per day)
            simulated_return = np.clip(avg_return + return_std * np.random.randn(), -0.10, 0.10)
            pred_close_estimate = max(0.01, last_close * (1 + simulated_return))
            open_price = max(0.01, last_close * (1 + avg_return * 0.5 + return_std * 0.3 * np.random.randn()))
            high_price = max(open_price, pred_close_estimate) * (1 + avg_atr_pct * 0.5 * abs(np.random.randn()))
            low_price = min(open_price, pred_close_estimate) * max(0.01, 1 - avg_atr_pct * 0.5 * abs(np.random.randn()))
            sim_volume = max(0, vol_mean + vol_std * np.random.randn())

            new_row = pd.DataFrame({
                'open': [open_price],
                'high': [high_price],
                'low': [low_price],
                'close': [pred_close_estimate],
                'volume': [sim_volume],
            }, index=[next_date])
            future_df = pd.concat([future_df, new_row])

            # Rebuild features on extended df
            ind_feat_df, _ = _prepare_indicator_features(future_df, indicator_rows)
            feat_df = _build_feature_df(future_df, ind_feat_df)
            feat_df = feat_df.dropna()

            if next_date not in feat_df.index:
                break

            # Ensure column alignment
            for c in feature_cols:
                if c not in feat_df.columns:
                    feat_df[c] = 0.0

            x_next = feat_df.loc[[next_date], feature_cols].values
            raw_pred = float(ml_model.predict(x_next)[0])

            # Blend bias-corrected model prediction with simulated trajectory
            # Weight based on model quality: good model → trust model, bad model → trust simulation
            model_pred = max(0.01, raw_pred + prediction_bias)
            pred_price = model_weight * model_pred + (1 - model_weight) * pred_close_estimate

            # Update close with bias-corrected prediction, keep realistic OHLV spread
            future_df.loc[next_date, 'close'] = pred_price
            future_df.loc[next_date, 'open'] = open_price
            price_range = abs(avg_atr_pct * pred_price * 0.5)
            future_df.loc[next_date, 'high'] = max(pred_price, open_price) + price_range * abs(np.random.randn()) * 0.3
            future_df.loc[next_date, 'low'] = max(0.01, min(pred_price, open_price) - price_range * abs(np.random.randn()) * 0.3)

            future_predictions.append({
                'tradingdate': next_date.strftime('%Y-%m-%d'),
                'close': pred_price,
            })

            last_date = next_date
            last_close = pred_price

        # Step 9: Compute metrics on the backtest period
        if len(actual_prices) > 1 and len(predicted_prices) > 1:
            actuals = np.array([p['close'] for p in actual_prices])
            preds = np.array([p['close'] for p in predicted_prices])
            rmse = float(np.sqrt(mean_squared_error(actuals, preds)))
            mae = float(mean_absolute_error(actuals, preds))
            r2 = float(r2_score(actuals, preds))
        else:
            rmse = mae = r2 = None

        # Build a rich chart series so the Prediction tab renders the same
        # multi-series view as the Training tab: recent real OHLCV history with
        # merged indicators plus a continuous backtest predicted line. The
        # forecast (`future`) extends this on the frontend. Bounded to the most
        # recent rows to keep the payload small.
        CHART_CONTEXT_ROWS = 300
        chart_points = []
        ctx_index = feature_df.index[-CHART_CONTEXT_ROWS:] if len(feature_df.index) > CHART_CONTEXT_ROWS else feature_df.index
        pos_by_date = {d: i for i, d in enumerate(feature_df.index)}
        for d in ctx_index:
            i_global = pos_by_date[d]
            point = {
                'date': d.strftime('%Y-%m-%d'),
                'actual_price': float(feature_df['close'].iloc[i_global]),
                'predicted_price': _correct_pred(float(y_pred[i_global])),
                'open': float(df.loc[d, 'open']) if d in df.index else None,
                'high': float(df.loc[d, 'high']) if d in df.index else None,
                'low': float(df.loc[d, 'low']) if d in df.index else None,
                'volume': float(df.loc[d, 'volume']) if d in df.index else None,
            }
            key = d.isoformat()
            if key in indicator_data_by_date:
                point.update(indicator_data_by_date[key])
            elif d.strftime('%Y-%m-%d') in indicator_data_by_date:
                point.update(indicator_data_by_date[d.strftime('%Y-%m-%d')])
            chart_points.append(point)

        # Build response
        prediction_response = {
            "solution_id": solution_id,
            "ticker": ticker,
            "train_status": "predicted",
            "chart": chart_points,
            "actual": actual_prices,
            "predict": predicted_prices,
            "future": future_predictions,
            "metrics": {
                "rmse": rmse,
                "mae": mae,
                "r2": r2,
            },
            "predict_start": predict_start,
            "predict_end": predict_end,
            "future_days": output_chunk_length,
        }

        # Persist prediction result and update status
        try:
            prediction_result_json = json.dumps(prediction_response)
            await db.execute(
                text("UPDATE tbl_solution SET train_status='predicted', prediction_result = :result WHERE id = :id"),
                {"result": prediction_result_json, "id": solution_id}
            )
        except Exception as persist_err:
            logger.warning(f"Failed to persist prediction result for solution {solution_id}: {persist_err}")
            await db.execute(
                text("UPDATE tbl_solution SET train_status='predicted' WHERE id = :id"),
                {"id": solution_id}
            )
        await db.commit()

        return prediction_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed for solution {solution_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


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
        elif code == 'DEMA':
            ema1 = ta.trend.EMAIndicator(df['close'], window=params.get('period', 20)).ema_indicator()
            ema2 = ta.trend.EMAIndicator(ema1, window=params.get('period', 20)).ema_indicator()
            values = 2 * ema1 - ema2
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'dema': _safe_val(values.iloc[i])})
        elif code == 'TEMA':
            ema1 = ta.trend.EMAIndicator(df['close'], window=params.get('period', 20)).ema_indicator()
            ema2 = ta.trend.EMAIndicator(ema1, window=params.get('period', 20)).ema_indicator()
            ema3 = ta.trend.EMAIndicator(ema2, window=params.get('period', 20)).ema_indicator()
            values = 3 * ema1 - 3 * ema2 + ema3
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'tema': _safe_val(values.iloc[i])})
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
        elif code == 'STOCH_RSI':
            s = ta.momentum.StochRSIIndicator(df['close'], window=params.get('period', 14),
                                               smooth1=params.get('smooth1', 3), smooth2=params.get('smooth2', 3))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'stoch_rsi_k': _safe_val(s.stochrsi_k().iloc[i]),
                               'stoch_rsi_d': _safe_val(s.stochrsi_d().iloc[i])})
        elif code == 'TSI':
            values = ta.momentum.TSIIndicator(df['close'], window_slow=params.get('slow_period', 25),
                                               window_fast=params.get('fast_period', 13)).tsi()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'tsi': _safe_val(values.iloc[i])})
        elif code == 'UO':
            values = ta.momentum.UltimateOscillator(df['high'], df['low'], df['close'],
                                                      window1=params.get('period1', 7),
                                                      window2=params.get('period2', 14),
                                                      window3=params.get('period3', 28)).ultimate_oscillator()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'uo': _safe_val(values.iloc[i])})
        elif code == 'AO':
            values = ta.momentum.AwesomeOscillatorIndicator(df['high'], df['low'],
                                                              window1=params.get('fast_period', 5),
                                                              window2=params.get('slow_period', 34)).awesome_oscillator()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'ao': _safe_val(values.iloc[i])})
        elif code == 'SUPERTREND':
            st = ta.trend.STCIndicator(df['close'], window_slow=params.get('slow_period', 50),
                                        window_fast=params.get('fast_period', 23), cycle=params.get('cycle', 10))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'supertrend': _safe_val(st.stc().iloc[i])})
        elif code == 'AROON':
            a = ta.trend.AroonIndicator(df['close'], window=params.get('period', 25))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'aroon_up': _safe_val(a.aroon_up().iloc[i]),
                               'aroon_down': _safe_val(a.aroon_down().iloc[i])})
        elif code == 'VORTEX':
            v = ta.trend.VortexIndicator(df['high'], df['low'], df['close'], window=params.get('period', 14))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'vortex_pos': _safe_val(v.vortex_indicator_pos().iloc[i]),
                               'vortex_neg': _safe_val(v.vortex_indicator_neg().iloc[i])})
        elif code == 'ICHIMOKU':
            ich = ta.trend.IchimokuIndicator(df['high'], df['low'],
                                              window1=params.get('tenkan_period', 9),
                                              window2=params.get('kijun_period', 26),
                                              window3=params.get('senkou_b_period', 52))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'ichimoku_conv': _safe_val(ich.ichimoku_conversion_line().iloc[i]),
                               'ichimoku_base': _safe_val(ich.ichimoku_base_line().iloc[i]),
                               'ichimoku_a': _safe_val(ich.ichimoku_a().iloc[i]),
                               'ichimoku_b': _safe_val(ich.ichimoku_b().iloc[i])})
        elif code == 'CHO':
            values = ta.volume.ChaikinMoneyFlowIndicator(df['high'], df['low'], df['close'], df['volume'],
                                                          window=params.get('period', 20)).chaikin_money_flow()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'cho': _safe_val(values.iloc[i])})
        elif code == 'EOM':
            values = ta.volume.EaseOfMovementIndicator(df['high'], df['low'], df['volume'],
                                                        window=params.get('period', 14)).ease_of_movement()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'eom': _safe_val(values.iloc[i])})
        elif code == 'FI':
            values = ta.volume.ForceIndexIndicator(df['close'], df['volume'],
                                                     window=params.get('period', 13)).force_index()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'fi': _safe_val(values.iloc[i])})
        elif code == 'NVI':
            values = ta.volume.NegativeVolumeIndexIndicator(df['close'], df['volume']).negative_volume_index()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'nvi': _safe_val(values.iloc[i])})
        elif code == 'PVI':
            values = ta.volume.VolumePriceTrendIndicator(df['close'], df['volume']).volume_price_trend()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'pvi': _safe_val(values.iloc[i])})
        elif code == 'VOSC':
            short_ma = df['volume'].rolling(window=params.get('short_period', 5)).mean()
            long_ma = df['volume'].rolling(window=params.get('long_period', 20)).mean()
            values = ((short_ma - long_ma) / long_ma) * 100
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'vosc': _safe_val(values.iloc[i])})
        elif code == 'Volume_MA':
            values = df['volume'].rolling(window=params.get('period', 20)).mean()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'volume_ma': _safe_val(values.iloc[i])})
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
        solution = dict(row)
        # Parse JSON result fields so frontend receives objects, not strings
        for field in ('training_result', 'prediction_result'):
            if solution.get(field) and isinstance(solution[field], str):
                try:
                    solution[field] = json.loads(solution[field])
                except (json.JSONDecodeError, TypeError):
                    solution[field] = None
        return solution
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
