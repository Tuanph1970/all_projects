"""
Pre-trained Model Prediction Strategy
Uses user's pre-trained models from solutions for predictions
"""

from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from services.prediction_strategies import PredictionStrategy
from services.model_service import ModelService
from services.indicator_service import IndicatorService
from repositories.predict_solution_repository import PredictSolutionRepository
from core.exceptions import PredictionException, EntityNotFoundException


class PretrainedPredictionStrategy(PredictionStrategy):
    """Strategy for using pre-trained models from solutions"""

    def __init__(self, solution_id: int):
        """
        Initialize with a trained solution

        Args:
            solution_id: ID of the trained solution to use
        """
        super().__init__(lookback_period=60)  # Will be overridden by model's actual lookback
        self.solution_id = solution_id
        self.solution_repo = PredictSolutionRepository()
        self.model_service = ModelService()
        self.indicator_service = IndicatorService()

        self.solution = None
        self.model_object = None
        self.uses_indicators = False

        # Load solution and model
        self._load_solution()

    def _load_solution(self):
        """Load the solution and its trained model"""
        # Get solution details
        self.solution = self.solution_repo.get_solution_by_id(self.solution_id)
        if not self.solution:
            raise EntityNotFoundException("Solution", str(self.solution_id))

        # Check if solution is trained
        if self.solution.get('solution_status') != 1:
            raise PredictionException(
                "PretrainedModel",
                f"Solution {self.solution_id} is not trained. Please train it first."
            )

        # Get model object with trained weights
        model_id = self.solution['model_id']
        model_name = self.solution.get('model_name', f"model_{model_id}")
        model_type = self.solution.get('model_type', 'unknown')

        self.model_object = self.model_service.get_model_by_id_with_file(
            model_id, model_name, model_type
        )

        # Set ticker
        ticker = self.solution['ticker']
        self.model_object.set_ticker(ticker=ticker)

        # Check if uses indicators
        validation = self.indicator_service.validate_solution_indicators(self.solution_id)
        self.uses_indicators = validation['is_valid']

        self.is_trained = True

    def build_model(self, input_shape: Tuple) -> None:
        """Model already built and trained"""
        pass  # Not needed, model is already trained

    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_val: np.ndarray = None, y_val: np.ndarray = None) -> Dict:
        """Model already trained"""
        return {
            'message': 'Using pre-trained model',
            'solution_id': self.solution_id,
            'training_period': f"{self.solution['start_training_date']} to {self.solution['end_training_date']}"
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions using the pre-trained model

        Note: This method signature is for compatibility.
        The actual prediction is done via predict_for_dates()
        """
        if not self.is_trained:
            raise PredictionException("PretrainedModel", "Model not loaded")

        # For pre-trained models, we need dates, not just X
        # This is a simplified version - use predict_for_dates() instead
        raise NotImplementedError(
            "Use predict_for_dates() for pre-trained models"
        )

    def predict_for_dates(self, start_date: str, end_date: str) -> Tuple[List, List]:
        """
        Make predictions for a specific date range using the pre-trained model

        Args:
            start_date: Start date for predictions (YYYY-MM-DD)
            end_date: End date for predictions (YYYY-MM-DD)

        Returns:
            Tuple of (dates, predictions)
        """
        if not self.is_trained:
            raise PredictionException("PretrainedModel", "Model not loaded")

        ticker = self.solution['ticker']

        # Calculate prediction length
        day_num = np.busday_count(start_date, end_date)
        predict_length = max(day_num, self.model_object.get_chunk_length())
        length = max(day_num, predict_length)

        # Adjust date range for data requirements
        adjusted_start = self._subtract_business_days(start_date, length)
        adjusted_end = self._add_business_days(end_date, length)

        # Prepare data based on whether solution uses indicators
        if self.uses_indicators:
            self._prepare_indicator_data(
                ticker,
                adjusted_start.strftime('%Y-%m-%d'),
                adjusted_end.strftime('%Y-%m-%d')
            )
        else:
            self._prepare_time_series_data(
                adjusted_start.strftime('%Y-%m-%d'),
                adjusted_end.strftime('%Y-%m-%d')
            )

        # Generate predictions using the model's predict method
        predict_json = self.model_object.predict(start_date, predict_length)

        # Extract dates and values
        dates = [p['tradingdate'] for p in predict_json]
        predictions = [p['close'] for p in predict_json]

        return dates, predictions

    def _prepare_indicator_data(self, ticker: str, start_date: str, end_date: str):
        """Prepare indicator data for prediction"""
        # Get solution indicators
        solution_indicators = self.indicator_service.get_solution_indicators(self.solution_id)

        # Calculate indicators
        calculated_indicators = self.indicator_service.calculate_solution_indicators({
            'solution_id': self.solution_id,
            'symbol': ticker,
            'start_date': start_date,
            'end_date': end_date
        })

        # Build DataFrame
        indicator_df = self.indicator_service.build_indicator_dataframe(calculated_indicators)

        # Add to model
        for col in indicator_df.columns:
            if col != 'date':
                self.model_object.add_field_from_dataframe(col, indicator_df[['date', col]])

                if col in solution_indicators and solution_indicators[col]:
                    covariate_type = solution_indicators[col].get('covariate_type', 'past')
                    if covariate_type == 'past':
                        self.model_object.add_past_covariate(col)
                    elif covariate_type == 'future':
                        self.model_object.add_future_covariate(col)
                    elif covariate_type == 'both':
                        self.model_object.add_past_covariate(col)
                        self.model_object.add_future_covariate(col)

        # Add target (close price)
        self.model_object.add_field('close', start_date, end_date)
        self.model_object.set_target_series('close')

    def _prepare_time_series_data(self, start_date: str, end_date: str):
        """Prepare time series data for prediction (legacy approach)"""
        from repositories.time_series_repository import TimeSeriesRepository
        from repositories.model_repository import ModelRepository

        time_series_repo = TimeSeriesRepository()
        model_repo = ModelRepository()

        model_db = model_repo.get_model_by_id(self.solution['model_id'])

        # Prepare indices
        idx = [{"name": "target", "value": str(self.solution['target'])}]

        if model_db['past_covariate']:
            past_idx = self.solution['past_covariate']
            for past_id in past_idx:
                idx.append({"name": "past", "value": str(past_id)})

        if model_db['future_covariate']:
            future_idx = self.solution['future_covariate']
            for future_id in future_idx:
                idx.append({"name": "future", "value": str(future_id)})

        # Load time series
        for series_info in idx:
            series = time_series_repo.get_series_by_id(int(series_info["value"]))
            if not series:
                raise EntityNotFoundException("Time Series", series_info["value"])

            name = series['series_type_name']
            self.model_object.add_field(name, start_date, end_date)

            if series_info["name"] == "target":
                self.model_object.set_target_series(name)
            elif series_info["name"] == "past":
                self.model_object.add_past_covariate(name)
            elif series_info["name"] == "future":
                self.model_object.add_future_covariate(name)

    def _add_business_days(self, from_date: str, add_days: int) -> datetime:
        """Add business days to a date"""
        date_format = '%Y-%m-%d'
        business_days_to_add = add_days
        current_date = datetime.strptime(from_date, date_format)

        while business_days_to_add > 0:
            current_date += timedelta(days=1)
            weekday = current_date.weekday()
            if weekday >= 5:
                continue
            business_days_to_add -= 1

        return current_date

    def _subtract_business_days(self, from_date: str, days: int) -> datetime:
        """Subtract business days from a date"""
        date_format = '%Y-%m-%d'
        business_days_to_subtract = days
        current_date = datetime.strptime(from_date, date_format)

        while business_days_to_subtract > 0:
            current_date += timedelta(days=-1)
            weekday = current_date.weekday()
            if weekday >= 5:
                continue
            business_days_to_subtract -= 1

        return current_date

    def get_model_name(self) -> str:
        """Return model name"""
        if self.solution:
            return f"Pretrained-{self.solution.get('solution_name', f'Solution{self.solution_id}')}"
        return "PretrainedModel"

    def get_solution_info(self) -> Dict:
        """Get solution information"""
        return {
            'solution_id': self.solution_id,
            'solution_name': self.solution.get('solution_name'),
            'ticker': self.solution.get('ticker'),
            'model_name': self.solution.get('model_name'),
            'model_type': self.solution.get('model_type'),
            'training_period': f"{self.solution['start_training_date']} to {self.solution['end_training_date']}"
        }
