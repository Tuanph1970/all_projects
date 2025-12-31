"""Pydantic Schemas for Prediction Service"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ModelType(str, Enum):
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    RANDOM_FOREST = "random_forest"
    LINEAR_REGRESSION = "linear_regression"
    ARIMA = "arima"
    LSTM = "lstm"


class ModelStatus(str, Enum):
    TRAINING = "training"
    READY = "ready"
    FAILED = "failed"
    DEPRECATED = "deprecated"


# Prediction Request/Response
class PredictionRequest(BaseModel):
    symbol: str = Field(..., max_length=20)
    days: int = Field(default=5, ge=1, le=30, description="Number of days to predict")
    model_type: Optional[ModelType] = Field(default=None, description="Model type to use")


class DailyPrediction(BaseModel):
    date: date
    predicted_price: float
    predicted_change: float
    direction: str  # up, down, neutral
    confidence: float
    price_low: Optional[float] = None
    price_high: Optional[float] = None


class PredictionResponse(BaseModel):
    symbol: str
    current_price: float
    predictions: List[DailyPrediction]
    model_type: str
    model_accuracy: Optional[float]
    generated_at: datetime


class BulkPredictionRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1, max_length=20)
    days: int = Field(default=5, ge=1, le=30)
    model_type: Optional[ModelType] = None


class BulkPredictionResponse(BaseModel):
    predictions: Dict[str, PredictionResponse]
    failed: List[str]
    generated_at: datetime


# Model Management
class ModelCreate(BaseModel):
    name: str = Field(..., max_length=255)
    model_type: ModelType
    symbol: Optional[str] = Field(default=None, max_length=20)
    hyperparameters: Optional[Dict[str, Any]] = None


class ModelResponse(BaseModel):
    id: int
    name: str
    model_type: ModelType
    symbol: Optional[str]
    version: str
    status: ModelStatus
    accuracy: Optional[float]
    mse: Optional[float]
    mae: Optional[float]
    rmse: Optional[float]
    r2_score: Optional[float]
    is_active: bool
    created_at: datetime
    trained_at: Optional[datetime]

    class Config:
        from_attributes = True


class ModelTrainRequest(BaseModel):
    symbol: Optional[str] = Field(default=None, max_length=20)
    model_type: ModelType = Field(default=ModelType.XGBOOST)
    lookback_days: int = Field(default=365, ge=30, le=1825)
    hyperparameters: Optional[Dict[str, Any]] = None


class ModelTrainResponse(BaseModel):
    model_id: int
    status: str
    message: str
    estimated_time_seconds: Optional[int]


class TrainingLogResponse(BaseModel):
    id: int
    model_id: int
    status: ModelStatus
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    training_samples: Optional[int]
    metrics: Optional[Dict[str, Any]]
    error_message: Optional[str]

    class Config:
        from_attributes = True


# Backtesting
class BacktestRequest(BaseModel):
    symbol: str = Field(..., max_length=20)
    model_type: ModelType = Field(default=ModelType.XGBOOST)
    start_date: date
    end_date: date
    prediction_horizon: int = Field(default=5, ge=1, le=30)


class BacktestResult(BaseModel):
    symbol: str
    model_type: str
    period: str
    total_predictions: int
    correct_direction: int
    direction_accuracy: float
    mean_absolute_error: float
    root_mean_squared_error: float
    average_confidence: float


# Model Comparison
class ModelComparisonRequest(BaseModel):
    symbol: str = Field(..., max_length=20)
    model_types: List[ModelType] = Field(default=[ModelType.XGBOOST, ModelType.LIGHTGBM])


class ModelComparisonResult(BaseModel):
    symbol: str
    comparisons: List[Dict[str, Any]]
    recommended_model: str
    recommendation_reason: str


# Prediction Accuracy Analysis
class AccuracyReport(BaseModel):
    model_id: int
    model_type: str
    symbol: Optional[str]
    period: str
    total_predictions: int
    accuracy_metrics: Dict[str, float]
    direction_accuracy: float
    average_error_percent: float


# Feature Importance
class FeatureImportance(BaseModel):
    feature: str
    importance: float
    description: Optional[str]


class FeatureImportanceResponse(BaseModel):
    model_id: int
    model_type: str
    features: List[FeatureImportance]


# Health & Status
class ModelHealthStatus(BaseModel):
    model_id: int
    name: str
    status: str
    last_trained: Optional[datetime]
    predictions_last_24h: int
    accuracy_last_30_days: Optional[float]
    needs_retraining: bool
