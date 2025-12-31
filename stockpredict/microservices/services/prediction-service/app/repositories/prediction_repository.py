"""Prediction Repository - Database Operations"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import MLModel, Prediction, ModelTrainingLog, PredictionRequest as PredictionRequestModel
from app.models.domain import ModelType, ModelStatus


class PredictionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ML Model Operations
    async def create_model(self, name: str, model_type: ModelType, symbol: Optional[str] = None,
                          version: str = "1.0.0", hyperparameters: Optional[dict] = None) -> MLModel:
        model = MLModel(
            name=name,
            model_type=model_type,
            symbol=symbol.upper() if symbol else None,
            version=version,
            status=ModelStatus.TRAINING,
            hyperparameters=hyperparameters
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model

    async def get_model_by_id(self, model_id: int) -> Optional[MLModel]:
        result = await self.session.execute(
            select(MLModel).where(MLModel.id == model_id)
        )
        return result.scalar_one_or_none()

    async def get_active_model(self, model_type: ModelType, symbol: Optional[str] = None) -> Optional[MLModel]:
        """Get the active model for a given type and symbol"""
        query = select(MLModel).where(
            and_(
                MLModel.model_type == model_type,
                MLModel.status == ModelStatus.READY,
                MLModel.is_active == True
            )
        )
        if symbol:
            query = query.where(MLModel.symbol == symbol.upper())
        else:
            query = query.where(MLModel.symbol.is_(None))

        query = query.order_by(MLModel.trained_at.desc())
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all_models(self, model_type: Optional[ModelType] = None,
                            symbol: Optional[str] = None,
                            active_only: bool = False) -> List[MLModel]:
        query = select(MLModel)
        conditions = []

        if model_type:
            conditions.append(MLModel.model_type == model_type)
        if symbol:
            conditions.append(MLModel.symbol == symbol.upper())
        if active_only:
            conditions.append(MLModel.is_active == True)
            conditions.append(MLModel.status == ModelStatus.READY)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(MLModel.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_model(self, model_id: int, **kwargs) -> Optional[MLModel]:
        kwargs["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(MLModel).where(MLModel.id == model_id).values(**kwargs)
        )
        await self.session.commit()
        return await self.get_model_by_id(model_id)

    async def update_model_metrics(self, model_id: int, accuracy: float, mse: float,
                                   mae: float, rmse: float, r2_score: float) -> Optional[MLModel]:
        return await self.update_model(
            model_id,
            accuracy=accuracy,
            mse=mse,
            mae=mae,
            rmse=rmse,
            r2_score=r2_score,
            status=ModelStatus.READY,
            trained_at=datetime.utcnow()
        )

    async def deactivate_old_models(self, model_type: ModelType, symbol: Optional[str] = None) -> int:
        """Deactivate old models when new one is trained"""
        query = update(MLModel).where(
            and_(
                MLModel.model_type == model_type,
                MLModel.is_active == True
            )
        )
        if symbol:
            query = query.where(MLModel.symbol == symbol.upper())
        else:
            query = query.where(MLModel.symbol.is_(None))

        result = await self.session.execute(query.values(is_active=False))
        await self.session.commit()
        return result.rowcount

    # Prediction Operations
    async def save_prediction(self, model_id: int, symbol: str, prediction_date: datetime,
                             target_date: datetime, predicted_price: float,
                             predicted_change: float, predicted_direction: str,
                             confidence: float, price_low: Optional[float] = None,
                             price_high: Optional[float] = None) -> Prediction:
        prediction = Prediction(
            model_id=model_id,
            symbol=symbol.upper(),
            prediction_date=prediction_date,
            target_date=target_date,
            predicted_price=predicted_price,
            predicted_change=predicted_change,
            predicted_direction=predicted_direction,
            confidence=confidence,
            price_low=price_low,
            price_high=price_high
        )
        self.session.add(prediction)
        await self.session.commit()
        await self.session.refresh(prediction)
        return prediction

    async def save_predictions_bulk(self, predictions: List[dict]) -> List[Prediction]:
        """Save multiple predictions at once"""
        saved = []
        for p in predictions:
            pred = Prediction(**p)
            self.session.add(pred)
            saved.append(pred)
        await self.session.commit()
        return saved

    async def get_predictions(self, symbol: str, start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None, limit: int = 100) -> List[Prediction]:
        query = select(Prediction).where(Prediction.symbol == symbol.upper())

        if start_date:
            query = query.where(Prediction.target_date >= start_date)
        if end_date:
            query = query.where(Prediction.target_date <= end_date)

        query = query.order_by(Prediction.target_date.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_predictions(self, symbol: str, days: int = 5) -> List[Prediction]:
        """Get the most recent predictions for a symbol"""
        result = await self.session.execute(
            select(Prediction)
            .where(
                and_(
                    Prediction.symbol == symbol.upper(),
                    Prediction.target_date >= datetime.utcnow()
                )
            )
            .order_by(Prediction.target_date.asc())
            .limit(days)
        )
        return list(result.scalars().all())

    async def update_prediction_actual(self, prediction_id: int, actual_price: float) -> Optional[Prediction]:
        """Update prediction with actual price for accuracy tracking"""
        prediction = await self.session.execute(
            select(Prediction).where(Prediction.id == prediction_id)
        )
        pred = prediction.scalar_one_or_none()
        if not pred:
            return None

        actual_change = ((actual_price - pred.predicted_price) / pred.predicted_price) * 100
        prediction_error = abs(actual_price - pred.predicted_price)
        is_correct = (pred.predicted_direction == "up" and actual_price > pred.predicted_price) or \
                    (pred.predicted_direction == "down" and actual_price < pred.predicted_price)

        await self.session.execute(
            update(Prediction)
            .where(Prediction.id == prediction_id)
            .values(
                actual_price=actual_price,
                actual_change=actual_change,
                prediction_error=prediction_error,
                is_correct=is_correct
            )
        )
        await self.session.commit()
        return await self.session.get(Prediction, prediction_id)

    # Training Log Operations
    async def create_training_log(self, model_id: int) -> ModelTrainingLog:
        log = ModelTrainingLog(model_id=model_id)
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def update_training_log(self, log_id: int, **kwargs) -> Optional[ModelTrainingLog]:
        await self.session.execute(
            update(ModelTrainingLog).where(ModelTrainingLog.id == log_id).values(**kwargs)
        )
        await self.session.commit()
        result = await self.session.execute(
            select(ModelTrainingLog).where(ModelTrainingLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def complete_training_log(self, log_id: int, status: ModelStatus,
                                   metrics: Optional[dict] = None,
                                   error_message: Optional[str] = None) -> Optional[ModelTrainingLog]:
        completed_at = datetime.utcnow()
        log = await self.session.get(ModelTrainingLog, log_id)
        if not log:
            return None

        duration = int((completed_at - log.started_at).total_seconds())
        return await self.update_training_log(
            log_id,
            status=status,
            completed_at=completed_at,
            duration_seconds=duration,
            metrics=metrics,
            error_message=error_message
        )

    async def get_training_logs(self, model_id: int, limit: int = 10) -> List[ModelTrainingLog]:
        result = await self.session.execute(
            select(ModelTrainingLog)
            .where(ModelTrainingLog.model_id == model_id)
            .order_by(ModelTrainingLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # Analytics
    async def log_prediction_request(self, user_id: Optional[int], symbol: str,
                                    model_type: str, prediction_days: int,
                                    request_ip: Optional[str] = None) -> None:
        request = PredictionRequestModel(
            user_id=user_id,
            symbol=symbol.upper(),
            model_type=model_type,
            prediction_days=prediction_days,
            request_ip=request_ip
        )
        self.session.add(request)
        await self.session.commit()

    async def get_model_accuracy_stats(self, model_id: int, days: int = 30) -> dict:
        """Get accuracy statistics for a model"""
        since = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            select(
                func.count(Prediction.id).label("total"),
                func.sum(func.cast(Prediction.is_correct, Integer)).label("correct"),
                func.avg(Prediction.prediction_error).label("avg_error")
            )
            .where(
                and_(
                    Prediction.model_id == model_id,
                    Prediction.actual_price.isnot(None),
                    Prediction.created_at >= since
                )
            )
        )
        row = result.fetchone()

        total = row.total or 0
        correct = row.correct or 0
        avg_error = float(row.avg_error) if row.avg_error else 0

        return {
            "total_predictions": total,
            "correct_predictions": correct,
            "direction_accuracy": (correct / total * 100) if total > 0 else 0,
            "average_error": avg_error
        }

    async def get_prediction_count_last_24h(self, model_id: int) -> int:
        since = datetime.utcnow() - timedelta(hours=24)
        result = await self.session.execute(
            select(func.count(Prediction.id))
            .where(
                and_(
                    Prediction.model_id == model_id,
                    Prediction.created_at >= since
                )
            )
        )
        return result.scalar() or 0


# Need to import Integer for the accuracy query
from sqlalchemy import Integer
