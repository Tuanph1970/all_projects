"""Domain Models for Prediction Service"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class ModelType(enum.Enum):
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    RANDOM_FOREST = "random_forest"
    LINEAR_REGRESSION = "linear_regression"
    ARIMA = "arima"
    LSTM = "lstm"


class ModelStatus(enum.Enum):
    TRAINING = "training"
    READY = "ready"
    FAILED = "failed"
    DEPRECATED = "deprecated"


class MLModel(Base):
    """Machine Learning Model metadata"""
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    model_type = Column(SQLEnum(ModelType), nullable=False)
    symbol = Column(String(20), nullable=True, index=True)  # Null means general model
    version = Column(String(50), nullable=False)
    status = Column(SQLEnum(ModelStatus), default=ModelStatus.TRAINING)
    file_path = Column(String(500), nullable=True)

    # Model metrics
    accuracy = Column(Float, nullable=True)
    mse = Column(Float, nullable=True)  # Mean Squared Error
    mae = Column(Float, nullable=True)  # Mean Absolute Error
    rmse = Column(Float, nullable=True)  # Root Mean Squared Error
    r2_score = Column(Float, nullable=True)

    # Training parameters
    hyperparameters = Column(JSON, nullable=True)
    feature_columns = Column(JSON, nullable=True)
    training_data_start = Column(DateTime, nullable=True)
    training_data_end = Column(DateTime, nullable=True)
    training_samples = Column(Integer, nullable=True)

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    trained_at = Column(DateTime, nullable=True)


class Prediction(Base):
    """Stock price predictions"""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)

    # Prediction details
    prediction_date = Column(DateTime, nullable=False)  # Date prediction was made
    target_date = Column(DateTime, nullable=False)  # Date prediction is for
    predicted_price = Column(Float, nullable=False)
    predicted_change = Column(Float, nullable=True)  # Percentage change
    predicted_direction = Column(String(10), nullable=True)  # up, down, neutral
    confidence = Column(Float, nullable=True)  # 0-1 confidence score

    # Prediction range
    price_low = Column(Float, nullable=True)
    price_high = Column(Float, nullable=True)

    # Actual results (filled in later)
    actual_price = Column(Float, nullable=True)
    actual_change = Column(Float, nullable=True)
    prediction_error = Column(Float, nullable=True)
    is_correct = Column(Boolean, nullable=True)  # Direction was correct

    created_at = Column(DateTime, default=datetime.utcnow)


class ModelTrainingLog(Base):
    """Training history and logs"""
    __tablename__ = "model_training_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, nullable=False, index=True)

    # Training info
    status = Column(SQLEnum(ModelStatus), default=ModelStatus.TRAINING)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Data info
    training_samples = Column(Integer, nullable=True)
    validation_samples = Column(Integer, nullable=True)
    features_used = Column(JSON, nullable=True)

    # Results
    metrics = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class PredictionRequest(Base):
    """Track prediction requests for analytics"""
    __tablename__ = "prediction_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    model_type = Column(String(50), nullable=True)
    prediction_days = Column(Integer, nullable=False)

    # Request metadata
    request_ip = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
