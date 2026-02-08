"""Prediction Service API Routes"""
import json
import logging
from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.dependencies import get_db, get_current_user_optional, get_current_user, require_admin
from app.services.prediction_service import PredictionService
from app.models.schemas import (
    PredictionRequest, PredictionResponse,
    BulkPredictionRequest, BulkPredictionResponse,
    ModelCreate, ModelResponse, ModelTrainRequest, ModelTrainResponse,
    BacktestRequest, BacktestResult,
    ModelComparisonRequest, ModelComparisonResult,
    FeatureImportanceResponse, AccuracyReport, ModelHealthStatus,
    ModelType, TrainingLogResponse
)

logger = logging.getLogger(__name__)

# Valid model type names (lowercase) mapped to proper case
MODEL_TYPE_MAP = {
    'blockrnn': 'BlockRNN', 'rnn': 'RNN', 'tcn': 'TCN',
    'transformer': 'Transformer', 'tft': 'TFT', 'nbeats': 'NBeats',
    'nhits': 'NHits', 'dlinear': 'DLinear', 'nlinear': 'NLinear',
    'xgboost': 'XGBoost', 'lightgbm': 'LightGBM',
    'randomforest': 'RandomForest', 'catboost': 'CatBoost', 'tide': 'TiDE'
}

router = APIRouter()


# Prediction Endpoints
@router.post("/predict", response_model=PredictionResponse)
async def predict_price(
    data: PredictionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Generate price prediction for a symbol"""
    service = PredictionService(db)

    # Log request
    await service.repo.log_prediction_request(
        user_id=current_user["user_id"] if current_user else None,
        symbol=data.symbol,
        model_type=data.model_type.value if data.model_type else "xgboost",
        prediction_days=data.days,
        request_ip=request.client.host if request.client else None
    )

    prediction = await service.predict(
        symbol=data.symbol,
        days=data.days,
        model_type=data.model_type
    )

    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not generate prediction for {data.symbol}"
        )

    return prediction


@router.get("/predict/{symbol}", response_model=PredictionResponse)
async def predict_price_get(
    symbol: str,
    days: int = Query(default=5, ge=1, le=30),
    model_type: Optional[ModelType] = Query(default=None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Generate price prediction for a symbol (GET endpoint)"""
    service = PredictionService(db)

    prediction = await service.predict(
        symbol=symbol,
        days=days,
        model_type=model_type
    )

    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not generate prediction for {symbol}"
        )

    return prediction


@router.post("/predict/bulk", response_model=BulkPredictionResponse)
async def predict_bulk(
    data: BulkPredictionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Generate predictions for multiple symbols"""
    service = PredictionService(db)
    predictions = {}
    failed = []

    for symbol in data.symbols:
        try:
            pred = await service.predict(symbol, data.days, data.model_type)
            if pred:
                predictions[symbol] = pred
            else:
                failed.append(symbol)
        except Exception as e:
            failed.append(symbol)

    return BulkPredictionResponse(
        predictions=predictions,
        failed=failed,
        generated_at=datetime.now()
    )


# Model Management Endpoints
@router.get("/models", response_model=List[ModelResponse])
async def list_models(
    model_type: Optional[ModelType] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    active_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db)
):
    """List available prediction models"""
    service = PredictionService(db)
    return await service.get_models(model_type, symbol, active_only)


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get model details by ID"""
    service = PredictionService(db)
    model = await service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post("/models/train", response_model=ModelTrainResponse)
async def train_model(
    data: ModelTrainRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Train a new prediction model"""
    service = PredictionService(db)
    return await service.train_model(
        model_type=data.model_type,
        symbol=data.symbol,
        lookback_days=data.lookback_days,
        hyperparameters=data.hyperparameters
    )


@router.get("/models/{model_id}/features", response_model=FeatureImportanceResponse)
async def get_feature_importance(
    model_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get feature importance for a model"""
    service = PredictionService(db)
    result = await service.get_feature_importance(model_id)
    if not result:
        raise HTTPException(status_code=404, detail="Model not found or no feature importance available")
    return result


@router.get("/models/{model_id}/training-logs", response_model=List[TrainingLogResponse])
async def get_training_logs(
    model_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get training history for a model"""
    service = PredictionService(db)
    logs = await service.repo.get_training_logs(model_id, limit)
    return [TrainingLogResponse.model_validate(log) for log in logs]


@router.delete("/models/{model_id}")
async def deactivate_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Deactivate a model (admin only)"""
    service = PredictionService(db)
    model = await service.repo.update_model(model_id, is_active=False)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model deactivated", "model_id": model_id}


# Backtesting Endpoints
@router.post("/backtest", response_model=BacktestResult)
async def run_backtest(
    data: BacktestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Run backtest on historical predictions"""
    service = PredictionService(db)
    result = await service.backtest(
        symbol=data.symbol,
        model_type=data.model_type,
        start_date=datetime.combine(data.start_date, datetime.min.time()),
        end_date=datetime.combine(data.end_date, datetime.min.time()),
        prediction_horizon=data.prediction_horizon
    )
    if not result:
        raise HTTPException(status_code=404, detail="No historical predictions found for backtest")
    return result


# Comparison Endpoints
@router.post("/compare", response_model=ModelComparisonResult)
async def compare_models(
    data: ModelComparisonRequest,
    db: AsyncSession = Depends(get_db)
):
    """Compare prediction accuracy of different models"""
    service = PredictionService(db)
    comparisons = []

    for mt in data.model_types:
        model = await service.repo.get_active_model(mt, data.symbol)
        if model:
            stats = await service.repo.get_model_accuracy_stats(model.id, days=30)
            comparisons.append({
                "model_type": mt.value,
                "model_id": model.id,
                "accuracy": model.accuracy,
                "direction_accuracy": stats["direction_accuracy"],
                "average_error": stats["average_error"],
                "predictions_count": stats["total_predictions"]
            })

    if not comparisons:
        raise HTTPException(status_code=404, detail="No models found for comparison")

    # Find best model
    best = max(comparisons, key=lambda x: x.get("accuracy", 0) or 0)

    return ModelComparisonResult(
        symbol=data.symbol,
        comparisons=comparisons,
        recommended_model=best["model_type"],
        recommendation_reason=f"Highest accuracy at {best['accuracy']:.2f}%"
    )


# Health & Status Endpoints
@router.get("/health/models", response_model=List[ModelHealthStatus])
async def get_models_health(
    db: AsyncSession = Depends(get_db)
):
    """Get health status of all active models"""
    service = PredictionService(db)
    models = await service.repo.get_all_models(active_only=True)

    health_status = []
    for model in models:
        pred_count = await service.repo.get_prediction_count_last_24h(model.id)
        stats = await service.repo.get_model_accuracy_stats(model.id, days=30)

        # Check if model needs retraining
        needs_retraining = False
        if model.trained_at:
            hours_since_training = (datetime.utcnow() - model.trained_at).total_seconds() / 3600
            needs_retraining = hours_since_training > 168  # 1 week

        health_status.append(ModelHealthStatus(
            model_id=model.id,
            name=model.name,
            status=model.status.value,
            last_trained=model.trained_at,
            predictions_last_24h=pred_count,
            accuracy_last_30_days=stats["direction_accuracy"] if stats["total_predictions"] > 0 else None,
            needs_retraining=needs_retraining
        ))

    return health_status


@router.get("/supported-models")
async def get_supported_models():
    """Get list of supported model types"""
    return {
        "models": [
            {
                "type": "xgboost",
                "name": "XGBoost",
                "description": "Gradient boosting ensemble method, good for structured data"
            },
            {
                "type": "lightgbm",
                "name": "LightGBM",
                "description": "Fast gradient boosting, efficient with large datasets"
            },
            {
                "type": "random_forest",
                "name": "Random Forest",
                "description": "Ensemble of decision trees, robust and interpretable"
            },
            {
                "type": "linear_regression",
                "name": "Linear Regression",
                "description": "Simple baseline model, fast and interpretable"
            },
            {
                "type": "arima",
                "name": "ARIMA",
                "description": "Time series model for trend and seasonality"
            }
        ]
    }


# ==========================================
# Simulation Endpoints
# ==========================================

@router.get("/simulation/models")
async def get_simulation_models():
    """Get list of available ML models for simulation"""
    return [
        {
            "model_type": "XGBoost",
            "description": "Gradient boosting ensemble, good for structured data"
        },
        {
            "model_type": "LightGBM",
            "description": "Fast gradient boosting, efficient with large datasets"
        },
        {
            "model_type": "Random Forest",
            "description": "Ensemble of decision trees, robust and interpretable"
        },
        {
            "model_type": "Linear Regression",
            "description": "Simple baseline model, fast and interpretable"
        },
        {
            "model_type": "LSTM",
            "description": "Deep learning model for sequential data"
        }
    ]


@router.get("/simulation/trained-solutions")
async def get_trained_solutions(
    current_user: dict = Depends(get_current_user_optional)
):
    """Get list of user's trained solutions for simulation"""
    # TODO: Implement trained solutions storage
    # For now, return empty list - users will train new models
    return []


# ==========================================
# Model Types Endpoints (for model management)
# ==========================================

@router.get("/types")
@router.get("/types/")
async def get_model_types():
    """Get all available model types with their sub-models"""
    # Returns model types in the format expected by the frontend
    # This matches the structure from webapi's get_all_model_types
    return [
        {
            "name": "BlockRNN",
            "sub_model": [
                {"name": "LSTM"},
                {"name": "GRU"},
                {"name": "RNN"}
            ]
        },
        {
            "name": "RNN",
            "sub_model": [
                {"name": "LSTM"},
                {"name": "GRU"},
                {"name": "Vanilla"}
            ]
        },
        {
            "name": "TCN",
            "sub_model": []
        },
        {
            "name": "Transformer",
            "sub_model": []
        },
        {
            "name": "TFT",
            "sub_model": []
        },
        {
            "name": "NBeats",
            "sub_model": []
        },
        {
            "name": "NHits",
            "sub_model": []
        },
        {
            "name": "DLinear",
            "sub_model": []
        },
        {
            "name": "NLinear",
            "sub_model": []
        },
        {
            "name": "XGBoost",
            "sub_model": []
        },
        {
            "name": "LightGBM",
            "sub_model": []
        },
        {
            "name": "RandomForest",
            "sub_model": []
        },
        {
            "name": "CatBoost",
            "sub_model": []
        }
    ]


# ==========================================
# Model Instance Management Endpoints
# (WebAPI-compatible endpoints for ModelList.js)
# ==========================================

@router.get("/all")
@router.get("/all/")
async def get_all_model_instances(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get all model instances (compatible with webapi's get_models endpoint)"""
    try:
        if current_user and current_user.get("user_id"):
            user_id = str(current_user["user_id"])
            result = await db.execute(
                text("SELECT id, model_name, model_type, model_sub_type, status, "
                     "file_path, created_at, updated_at, created_by "
                     "FROM model_instances WHERE user_id = :user_id ORDER BY id DESC"),
                {"user_id": user_id}
            )
        else:
            result = await db.execute(
                text("SELECT id, model_name, model_type, model_sub_type, status, "
                     "file_path, created_at, updated_at, created_by "
                     "FROM model_instances ORDER BY id DESC")
            )
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.warning(f"Failed to fetch model instances: {e}")
        return []


@router.get("/parameters")
@router.get("/parameters/")
async def get_model_parameter_fields(
    db: AsyncSession = Depends(get_db)
):
    """Get model parameter field definitions from tbl_model_field.

    Returns pivoted data: one object per model_type_ with field_name->field_type mappings.
    Frontend expects: [{"model_type_": "BlockRNN", "input_chunk_length": "text", ...}, ...]
    """
    try:
        result = await db.execute(
            text("SELECT model_type_, field_name, field_type FROM tbl_model_field ORDER BY model_type_, display_order")
        )
        rows = result.mappings().all()
        # Pivot: group by model_type_, field_name becomes key, field_type becomes value
        pivoted = {}
        for row in rows:
            mt = row["model_type_"]
            if mt not in pivoted:
                pivoted[mt] = {"model_type_": mt}
            pivoted[mt][row["field_name"]] = row["field_type"]
        return list(pivoted.values())
    except Exception as e:
        logger.warning(f"Failed to fetch model parameter fields: {e}")
        return []


@router.get("/parameters/default-values")
@router.get("/parameters/default-values/")
async def get_model_default_values(
    db: AsyncSession = Depends(get_db)
):
    """Get default parameter values for all model types from tbl_model_defaul_value.

    Returns pivoted data: one object per model_type_ with field_name->default_value mappings.
    Frontend expects: [{"model_type_": "BlockRNN", "input_chunk_length": "14", ...}, ...]
    """
    try:
        result = await db.execute(
            text("SELECT model_type_, field_name, default_value FROM tbl_model_defaul_value ORDER BY model_type_")
        )
        rows = result.mappings().all()
        # Pivot: group by model_type_, field_name becomes key, default_value becomes value
        pivoted = {}
        for row in rows:
            mt = row["model_type_"]
            if mt not in pivoted:
                pivoted[mt] = {"model_type_": mt}
            pivoted[mt][row["field_name"]] = row["default_value"]
        return list(pivoted.values())
    except Exception as e:
        logger.warning(f"Failed to fetch default parameter values: {e}")
        return []


@router.get("/params/options")
@router.get("/params/options/")
async def get_parameter_options(
    db: AsyncSession = Depends(get_db)
):
    """Get available options for model parameters from tbl_param_option"""
    try:
        result = await db.execute(
            text("SELECT param_name, GROUP_CONCAT(option_value) as options "
                 "FROM tbl_param_option GROUP BY param_name")
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.warning(f"Failed to fetch parameter options: {e}")
        return []


# ==========================================
# Technical Indicators Endpoints
# IMPORTANT: Must be declared BEFORE catch-all /{model_id_or_type} routes
# ==========================================

@router.get("/indicators")
@router.get("/indicators/")
async def get_all_indicators(
    db: AsyncSession = Depends(get_db)
):
    """Get all technical indicators grouped by category"""
    try:
        result = await db.execute(
            text("SELECT id, name, type, description, calculation_function, default_parameters "
                 "FROM technical_indicators ORDER BY type, name")
        )
        rows = result.mappings().all()

        grouped = {
            'trend': [], 'momentum': [], 'volatility': [], 'volume': [],
            'support_resistance': [], 'price_transform': [], 'bill_williams': []
        }

        for row in rows:
            params = json.loads(row['default_parameters']) if row['default_parameters'] else {}
            indicator = {
                'id': row['id'],
                'name': row['name'],
                'type': row['type'],
                'description': row['description'],
                'calculation_function': row['calculation_function'],
                'default_parameters': params
            }
            category = row['type']
            if category in grouped:
                grouped[category].append(indicator)
            else:
                grouped[category] = [indicator]

        return grouped
    except Exception as e:
        logger.error(f"Failed to fetch indicators: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch indicators: {str(e)}")


@router.get("/indicators/type/{indicator_type}")
@router.get("/indicators/type/{indicator_type}/")
async def get_indicators_by_type(
    indicator_type: str,
    db: AsyncSession = Depends(get_db)
):
    """Get indicators filtered by type"""
    try:
        result = await db.execute(
            text("SELECT id, name, type, description, calculation_function, default_parameters "
                 "FROM technical_indicators WHERE type = :indicator_type ORDER BY name"),
            {"indicator_type": indicator_type}
        )
        rows = result.mappings().all()
        return [{
            'id': row['id'],
            'name': row['name'],
            'type': row['type'],
            'description': row['description'],
            'calculation_function': row['calculation_function'],
            'default_parameters': json.loads(row['default_parameters']) if row['default_parameters'] else {}
        } for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch indicators by type: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch indicators: {str(e)}")


@router.get("/indicators/{indicator_id}")
@router.get("/indicators/{indicator_id}/")
async def get_indicator_by_id(
    indicator_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get specific indicator details"""
    try:
        result = await db.execute(
            text("SELECT id, name, type, description, calculation_function, default_parameters "
                 "FROM technical_indicators WHERE id = :indicator_id"),
            {"indicator_id": indicator_id}
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Indicator {indicator_id} not found")
        return {
            'id': row['id'],
            'name': row['name'],
            'type': row['type'],
            'description': row['description'],
            'calculation_function': row['calculation_function'],
            'default_parameters': json.loads(row['default_parameters']) if row['default_parameters'] else {}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch indicator: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch indicator: {str(e)}")


@router.post("/indicators")
@router.post("/indicators/")
async def create_indicator(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Create a new technical indicator"""
    data = await request.json()
    name = data.get('name')
    indicator_type = data.get('type')
    description = data.get('description', '')
    calculation_function = data.get('calculation_function', '')
    default_parameters = data.get('default_parameters', {})

    if not name or not indicator_type:
        raise HTTPException(status_code=400, detail="name and type are required")

    try:
        params_json = json.dumps(default_parameters) if isinstance(default_parameters, dict) else default_parameters
        result = await db.execute(
            text("INSERT INTO technical_indicators (name, type, description, calculation_function, default_parameters) "
                 "VALUES (:name, :type, :description, :calc_func, :params)"),
            {"name": name, "type": indicator_type, "description": description,
             "calc_func": calculation_function, "params": params_json}
        )
        await db.commit()
        return {
            'id': result.lastrowid,
            'name': name,
            'type': indicator_type,
            'description': description,
            'calculation_function': calculation_function,
            'default_parameters': default_parameters
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create indicator: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create indicator: {str(e)}")


@router.put("/indicators/{indicator_id}")
@router.put("/indicators/{indicator_id}/")
async def update_indicator(
    indicator_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Update an existing technical indicator"""
    data = await request.json()
    updates = []
    values = {"indicator_id": indicator_id}

    for field in ['name', 'type', 'description', 'calculation_function']:
        if field in data:
            updates.append(f"{field} = :{field}")
            values[field] = data[field]

    if 'default_parameters' in data:
        updates.append("default_parameters = :default_parameters")
        values['default_parameters'] = json.dumps(data['default_parameters']) if isinstance(data['default_parameters'], dict) else data['default_parameters']

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        query = f"UPDATE technical_indicators SET {', '.join(updates)} WHERE id = :indicator_id"
        result = await db.execute(text(query), values)
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Indicator {indicator_id} not found")
        return {"message": "Indicator updated", "id": indicator_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update indicator: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update indicator: {str(e)}")


@router.delete("/indicators/{indicator_id}")
@router.delete("/indicators/{indicator_id}/")
async def delete_indicator(
    indicator_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Delete a technical indicator"""
    try:
        result = await db.execute(
            text("DELETE FROM technical_indicators WHERE id = :indicator_id"),
            {"indicator_id": indicator_id}
        )
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Indicator {indicator_id} not found")
        return {"message": "Indicator deleted", "id": indicator_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete indicator: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete indicator: {str(e)}")


# ==========================================
# Catch-all Model Instance Endpoints
# IMPORTANT: These must come AFTER all specific routes
# ==========================================

@router.get("/{model_id_or_type}")
async def get_model_instance_by_id(
    model_id_or_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get a model instance by ID from model_instances table.

    The frontend calls GET /models/{id} to load model config for editing.
    We check if the path param is numeric (model ID) vs a model type name.
    """
    # Only handle numeric IDs - let other paths fall through to 404
    if not model_id_or_type.isdigit():
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id_or_type}")

    model_id = int(model_id_or_type)
    try:
        result = await db.execute(
            text("SELECT id, model_name, model_type, model_sub_type, status, "
                 "config_json, file_path, created_at, updated_at, created_by, user_id "
                 "FROM model_instances WHERE id = :model_id"),
            {"model_id": model_id}
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Model instance {model_id} not found")

        data = dict(row)
        # Parse config_json and merge into response so the edit form gets all fields
        if data.get("config_json"):
            try:
                config = json.loads(data["config_json"])
                data.update(config)
            except (json.JSONDecodeError, TypeError):
                pass
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch model instance {model_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch model: {str(e)}")


@router.delete("/{model_id_str}")
async def delete_model_instance(
    model_id_str: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Delete a model instance by ID, including associated files on disk.

    Cleanup covers:
    - The file at file_path (stored in DB)
    - User model directory: {MODEL_PATH}/{user_id}/model_{id}.*
    - Versioned snapshots: {MODEL_PATH}/{user_id}/model_{id}_versions/
    """
    import os
    import shutil
    from app.config import get_settings

    if not model_id_str.isdigit():
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id_str}")

    model_id = int(model_id_str)
    settings = get_settings()
    deleted_files = []

    try:
        # Fetch model info before deleting (need file_path and user_id for cleanup)
        result = await db.execute(
            text("SELECT id, file_path, user_id, model_name FROM model_instances WHERE id = :model_id"),
            {"model_id": model_id}
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Model instance {model_id} not found")

        file_path = row.get("file_path")
        user_id = str(row.get("user_id", ""))
        model_name = row.get("model_name", "")

        # 1. Delete the specific file_path stored in DB
        if file_path:
            abs_path = os.path.join(settings.MODEL_PATH, file_path)
            if os.path.exists(abs_path):
                os.remove(abs_path)
                deleted_files.append(abs_path)
                logger.info(f"Deleted model file: {abs_path}")
                # Remove parent dir if empty
                parent = os.path.dirname(abs_path)
                if parent and os.path.isdir(parent) and not os.listdir(parent):
                    os.rmdir(parent)
                    deleted_files.append(parent)

        # 2. Clean up user model files matching model_{id}.* pattern
        if user_id:
            user_dir = os.path.join(settings.MODEL_PATH, user_id)
            if os.path.isdir(user_dir):
                for fname in os.listdir(user_dir):
                    if fname.startswith(f"model_{model_id}.") or fname.startswith(f"model_{model_id}_"):
                        fpath = os.path.join(user_dir, fname)
                        if os.path.isfile(fpath):
                            os.remove(fpath)
                            deleted_files.append(fpath)
                            logger.info(f"Deleted model file: {fpath}")

                # 3. Delete versioned snapshots directory
                versions_dir = os.path.join(user_dir, f"model_{model_id}_versions")
                if os.path.isdir(versions_dir):
                    shutil.rmtree(versions_dir)
                    deleted_files.append(versions_dir)
                    logger.info(f"Deleted versions directory: {versions_dir}")

                # 4. Delete model_name subdirectory if it exists and contains model files
                if model_name:
                    model_name_dir = os.path.join(user_dir, model_name)
                    if os.path.isdir(model_name_dir):
                        shutil.rmtree(model_name_dir)
                        deleted_files.append(model_name_dir)
                        logger.info(f"Deleted model name directory: {model_name_dir}")

        # Delete from database
        await db.execute(
            text("DELETE FROM model_instances WHERE id = :model_id"),
            {"model_id": model_id}
        )
        await db.commit()

        return {
            "message": "Model deleted successfully",
            "model_id": model_id,
            "deleted_files": len(deleted_files)
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete model instance {model_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")


@router.post("/{model_type_name}")
async def create_model_by_type(
    model_type_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Create a model instance by type (compatible with webapi's type-specific endpoints)"""
    model_type = MODEL_TYPE_MAP.get(model_type_name.lower())
    if not model_type:
        raise HTTPException(status_code=404, detail=f"Unknown model type: {model_type_name}")

    data = await request.json()
    user_id = str(current_user["user_id"]) if current_user else "default_user"
    model_name = data.get('model_name', f'{model_type} Model')
    model_sub_type = data.get('model_sub_type', data.get('model', ''))

    # Extract configuration parameters (exclude metadata fields)
    parameters = {k: v for k, v in data.items()
                  if k not in ['model_name', 'model_type', 'model_sub_type']}

    try:
        config_json = json.dumps(parameters)
        result = await db.execute(
            text("INSERT INTO model_instances "
                 "(model_name, model_type, model_sub_type, user_id, status, "
                 "config_json, created_by, created_at, updated_at) "
                 "VALUES (:model_name, :model_type, :model_sub_type, :user_id, 'created', "
                 ":config_json, :created_by, NOW(), NOW())"),
            {
                "model_name": model_name,
                "model_type": model_type,
                "model_sub_type": model_sub_type,
                "user_id": user_id,
                "config_json": config_json,
                "created_by": user_id
            }
        )
        await db.commit()
        model_id = result.lastrowid

        return {
            "model_id": model_id,
            "model_name": model_name,
            "model_type": model_type,
            "model_sub_type": model_sub_type,
            "status": "created",
            "configuration": parameters
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create model: {str(e)}")


@router.put("/{model_type_name}")
async def update_model_by_type(
    model_type_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Update a model instance by type (compatible with webapi's type-specific endpoints)"""
    model_type = MODEL_TYPE_MAP.get(model_type_name.lower())
    if not model_type:
        raise HTTPException(status_code=404, detail=f"Unknown model type: {model_type_name}")

    data = await request.json()
    model_id = data.get('model_id')
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id is required")

    model_name = data.get('model_name')
    model_sub_type = data.get('model_sub_type', data.get('model', ''))

    # Extract configuration parameters (exclude metadata fields)
    parameters = {k: v for k, v in data.items()
                  if k not in ['model_name', 'model_type', 'model_sub_type', 'model_id']}

    try:
        config_json = json.dumps(parameters)
        await db.execute(
            text("UPDATE model_instances SET model_name = :model_name, "
                 "model_sub_type = :model_sub_type, config_json = :config_json, "
                 "updated_at = NOW() WHERE id = :model_id"),
            {
                "model_name": model_name,
                "model_sub_type": model_sub_type,
                "config_json": config_json,
                "model_id": model_id
            }
        )
        await db.commit()

        return {
            "model_id": model_id,
            "model_name": model_name,
            "model_sub_type": model_sub_type,
            "status": "updated",
            "configuration": parameters
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update model: {str(e)}")
