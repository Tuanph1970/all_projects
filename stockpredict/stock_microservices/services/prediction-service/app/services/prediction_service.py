"""Prediction Service - ML Business Logic"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import lightgbm as lgb
import httpx
import joblib
import os
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repositories.prediction_repository import PredictionRepository
from app.models.domain import ModelType, ModelStatus
from app.models.schemas import (
    PredictionResponse, DailyPrediction, ModelResponse,
    ModelTrainResponse, BacktestResult, FeatureImportance, FeatureImportanceResponse
)

settings = get_settings()
logger = logging.getLogger(__name__)


class PredictionService:
    def __init__(self, session: AsyncSession):
        self.repo = PredictionRepository(session)
        self.session = session

    async def _fetch_historical_data(self, symbol: str, days: int = 365) -> Optional[pd.DataFrame]:
        """Fetch historical price data from stock-data-service"""
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}/api/v2/stocks/{symbol}/history",
                    params={"start_date": start_date, "end_date": end_date},
                    timeout=60.0
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data"):
                        df = pd.DataFrame(data["data"])
                        df["date"] = pd.to_datetime(df["date"])
                        df = df.sort_values("date")
                        return df
        except Exception as e:
            logger.error(f"Failed to fetch historical data for {symbol}: {e}")
        return None

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from stock-data-service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}/api/v2/stocks/{symbol}/quote",
                    timeout=30.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("price") or data.get("close")
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
        return None

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare technical features for prediction"""
        df = df.copy()

        # Price-based features
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))

        # Moving averages
        for period in [5, 10, 20, 50]:
            df[f"sma_{period}"] = df["close"].rolling(window=period).mean()
            df[f"ema_{period}"] = df["close"].ewm(span=period).mean()

        # Volatility
        df["volatility_20"] = df["returns"].rolling(window=20).std()
        df["volatility_5"] = df["returns"].rolling(window=5).std()

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # MACD
        df["macd"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
        df["macd_signal"] = df["macd"].ewm(span=9).mean()

        # Bollinger Bands
        df["bb_middle"] = df["close"].rolling(window=20).mean()
        bb_std = df["close"].rolling(window=20).std()
        df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
        df["bb_lower"] = df["bb_middle"] - (bb_std * 2)
        df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

        # Volume features
        if "volume" in df.columns:
            df["volume_sma_20"] = df["volume"].rolling(window=20).mean()
            df["volume_ratio"] = df["volume"] / df["volume_sma_20"]

        # Lag features
        for lag in [1, 2, 3, 5]:
            df[f"close_lag_{lag}"] = df["close"].shift(lag)
            df[f"returns_lag_{lag}"] = df["returns"].shift(lag)

        # Target: next day's closing price
        df["target"] = df["close"].shift(-1)

        return df.dropna()

    def _get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Get feature columns for training"""
        exclude = ["date", "target", "symbol", "open", "high", "low", "close", "volume"]
        return [col for col in df.columns if col not in exclude and not col.startswith("Unnamed")]

    async def train_model(self, model_type: ModelType, symbol: Optional[str] = None,
                         lookback_days: int = 365, hyperparameters: Optional[dict] = None) -> ModelTrainResponse:
        """Train a new prediction model"""
        # Fetch training data
        df = await self._fetch_historical_data(symbol or "VNM", lookback_days)
        if df is None or len(df) < 60:
            return ModelTrainResponse(
                model_id=0,
                status="failed",
                message="Insufficient historical data for training",
                estimated_time_seconds=None
            )

        # Prepare features
        df = self._prepare_features(df)
        feature_cols = self._get_feature_columns(df)

        X = df[feature_cols]
        y = df["target"]

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

        # Create model record
        model = await self.repo.create_model(
            name=f"{model_type.value}_{symbol or 'general'}_{datetime.now().strftime('%Y%m%d')}",
            model_type=model_type,
            symbol=symbol,
            version="1.0.0",
            hyperparameters=hyperparameters
        )

        # Create training log
        log = await self.repo.create_training_log(model.id)

        try:
            # Train model based on type
            if model_type == ModelType.XGBOOST:
                params = hyperparameters or {
                    "n_estimators": 100,
                    "max_depth": 6,
                    "learning_rate": 0.1
                }
                ml_model = xgb.XGBRegressor(**params)
            elif model_type == ModelType.LIGHTGBM:
                params = hyperparameters or {
                    "n_estimators": 100,
                    "max_depth": 6,
                    "learning_rate": 0.1,
                    "verbose": -1
                }
                ml_model = lgb.LGBMRegressor(**params)
            elif model_type == ModelType.RANDOM_FOREST:
                params = hyperparameters or {
                    "n_estimators": 100,
                    "max_depth": 10
                }
                ml_model = RandomForestRegressor(**params)
            else:
                ml_model = LinearRegression()

            # Fit model
            ml_model.fit(X_train, y_train)

            # Evaluate
            y_pred = ml_model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_test, y_pred)

            # Calculate direction accuracy
            actual_direction = np.sign(y_test.values - X_test["close_lag_1"].values)
            pred_direction = np.sign(y_pred - X_test["close_lag_1"].values)
            accuracy = (actual_direction == pred_direction).mean() * 100

            # Save model file
            os.makedirs(settings.MODEL_PATH, exist_ok=True)
            model_path = f"{settings.MODEL_PATH}/{model.id}_{model_type.value}.joblib"
            joblib.dump(ml_model, model_path)

            # Update model metrics
            await self.repo.update_model(
                model.id,
                file_path=model_path,
                accuracy=accuracy,
                mse=mse,
                mae=mae,
                rmse=rmse,
                r2_score=r2,
                feature_columns=feature_cols,
                training_data_start=df["date"].min(),
                training_data_end=df["date"].max(),
                training_samples=len(X_train),
                status=ModelStatus.READY
            )

            # Complete training log
            await self.repo.complete_training_log(
                log.id,
                status=ModelStatus.READY,
                metrics={"mse": mse, "mae": mae, "rmse": rmse, "r2": r2, "accuracy": accuracy}
            )

            # Deactivate old models
            await self.repo.deactivate_old_models(model_type, symbol)
            await self.repo.update_model(model.id, is_active=True)

            return ModelTrainResponse(
                model_id=model.id,
                status="completed",
                message=f"Model trained successfully. Accuracy: {accuracy:.2f}%",
                estimated_time_seconds=None
            )

        except Exception as e:
            logger.error(f"Model training failed: {e}")
            await self.repo.update_model(model.id, status=ModelStatus.FAILED)
            await self.repo.complete_training_log(log.id, status=ModelStatus.FAILED, error_message=str(e))
            return ModelTrainResponse(
                model_id=model.id,
                status="failed",
                message=str(e),
                estimated_time_seconds=None
            )

    async def predict(self, symbol: str, days: int = 5,
                     model_type: Optional[ModelType] = None) -> Optional[PredictionResponse]:
        """Generate price predictions"""
        # Get active model
        mt = model_type or ModelType.XGBOOST
        model = await self.repo.get_active_model(mt, symbol)

        if not model:
            # Try general model
            model = await self.repo.get_active_model(mt, None)

        if not model or not model.file_path:
            # Train a new model if none exists
            train_result = await self.train_model(mt, symbol)
            if train_result.status != "completed":
                return None
            model = await self.repo.get_model_by_id(train_result.model_id)

        try:
            # Load model
            ml_model = joblib.load(model.file_path)

            # Fetch recent data
            df = await self._fetch_historical_data(symbol, settings.LOOKBACK_PERIOD)
            if df is None:
                return None

            # Prepare features
            df = self._prepare_features(df)
            feature_cols = model.feature_columns or self._get_feature_columns(df)

            # Get current price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                current_price = df["close"].iloc[-1]

            # Generate predictions
            predictions = []
            last_row = df[feature_cols].iloc[-1:].copy()

            for day in range(1, days + 1):
                pred_price = ml_model.predict(last_row)[0]
                change_pct = ((pred_price - current_price) / current_price) * 100

                # Calculate confidence based on volatility
                volatility = df["volatility_20"].iloc[-1] if "volatility_20" in df.columns else 0.02
                confidence = max(0.5, min(0.95, 1 - volatility * 10))

                # Prediction range
                price_low = pred_price * (1 - volatility)
                price_high = pred_price * (1 + volatility)

                direction = "up" if pred_price > current_price else ("down" if pred_price < current_price else "neutral")

                target_date = datetime.now() + timedelta(days=day)

                # Save prediction
                await self.repo.save_prediction(
                    model_id=model.id,
                    symbol=symbol,
                    prediction_date=datetime.now(),
                    target_date=target_date,
                    predicted_price=pred_price,
                    predicted_change=change_pct,
                    predicted_direction=direction,
                    confidence=confidence,
                    price_low=price_low,
                    price_high=price_high
                )

                predictions.append(DailyPrediction(
                    date=target_date.date(),
                    predicted_price=round(pred_price, 2),
                    predicted_change=round(change_pct, 2),
                    direction=direction,
                    confidence=round(confidence, 3),
                    price_low=round(price_low, 2),
                    price_high=round(price_high, 2)
                ))

                # Update features for next prediction (simplified)
                current_price = pred_price

            return PredictionResponse(
                symbol=symbol.upper(),
                current_price=await self._get_current_price(symbol) or df["close"].iloc[-1],
                predictions=predictions,
                model_type=model.model_type.value,
                model_accuracy=model.accuracy,
                generated_at=datetime.now()
            )

        except Exception as e:
            logger.error(f"Prediction failed for {symbol}: {e}")
            return None

    async def get_models(self, model_type: Optional[ModelType] = None,
                        symbol: Optional[str] = None,
                        active_only: bool = False) -> List[ModelResponse]:
        """Get available models"""
        models = await self.repo.get_all_models(model_type, symbol, active_only)
        return [ModelResponse.model_validate(m) for m in models]

    async def get_model(self, model_id: int) -> Optional[ModelResponse]:
        """Get model by ID"""
        model = await self.repo.get_model_by_id(model_id)
        return ModelResponse.model_validate(model) if model else None

    async def get_feature_importance(self, model_id: int) -> Optional[FeatureImportanceResponse]:
        """Get feature importance for a model"""
        model = await self.repo.get_model_by_id(model_id)
        if not model or not model.file_path:
            return None

        try:
            ml_model = joblib.load(model.file_path)
            feature_cols = model.feature_columns or []

            if hasattr(ml_model, "feature_importances_"):
                importances = ml_model.feature_importances_
                features = [
                    FeatureImportance(
                        feature=feature_cols[i],
                        importance=float(importances[i]),
                        description=None
                    )
                    for i in range(len(feature_cols))
                ]
                features.sort(key=lambda x: x.importance, reverse=True)

                return FeatureImportanceResponse(
                    model_id=model.id,
                    model_type=model.model_type.value,
                    features=features[:20]  # Top 20 features
                )
        except Exception as e:
            logger.error(f"Failed to get feature importance: {e}")

        return None

    async def backtest(self, symbol: str, model_type: ModelType,
                      start_date: datetime, end_date: datetime,
                      prediction_horizon: int = 5) -> Optional[BacktestResult]:
        """Backtest a prediction model"""
        # Simplified backtest implementation
        predictions = await self.repo.get_predictions(symbol, start_date, end_date, limit=1000)
        if not predictions:
            return None

        total = len(predictions)
        correct = sum(1 for p in predictions if p.is_correct)
        mae = sum(p.prediction_error or 0 for p in predictions) / total if total > 0 else 0
        avg_conf = sum(p.confidence or 0 for p in predictions) / total if total > 0 else 0

        return BacktestResult(
            symbol=symbol,
            model_type=model_type.value,
            period=f"{start_date.date()} to {end_date.date()}",
            total_predictions=total,
            correct_direction=correct,
            direction_accuracy=correct / total * 100 if total > 0 else 0,
            mean_absolute_error=mae,
            root_mean_squared_error=np.sqrt(mae),
            average_confidence=avg_conf
        )
