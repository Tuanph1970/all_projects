"""Prediction Service API Routes"""
from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

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
