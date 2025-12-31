"""
Date Range Calculator for Stock Prediction Models

This utility automatically calculates the required date range for model training
based on model parameters and validation requirements.
"""

from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import numpy as np


class DateRangeCalculator:
    """
    Calculate optimal date ranges for time series model training.

    Ensures sufficient data points for both training and validation based on:
    - Model input/output chunk lengths
    - Validation settings and train ratio
    - Safety margins for data quality
    """

    # Safety multipliers to ensure sufficient data
    SAFETY_MARGIN_MULTIPLIER = 1.5  # 50% extra data for safety
    MIN_TRAINING_SAMPLES = 10  # Minimum number of training samples
    MIN_VALIDATION_SAMPLES = 5  # Minimum number of validation samples
    BUSINESS_DAYS_PER_MONTH = 21  # Average business days per month

    def __init__(self):
        pass

    def calculate_required_data_points(
        self,
        model_object,
        validation: bool = True,
        train_ratio: float = 0.8
    ) -> Dict[str, int]:
        """
        Calculate the minimum number of data points required for training.

        Args:
            model_object: The model instance with configuration parameters
            validation: Whether validation is enabled
            train_ratio: Ratio of data used for training (0.0 to 1.0)

        Returns:
            Dict with data point requirements:
            {
                'min_sample_length': Minimum points for one sample,
                'min_train_points': Minimum points for training set,
                'min_val_points': Minimum points for validation set,
                'total_required': Total points needed,
                'recommended': Recommended points with safety margin
            }
        """
        # Get model parameters
        input_chunk = getattr(model_object, 'input_chunk_length', 14)
        output_chunk = getattr(model_object, 'output_chunk_length', 10)
        training_length = getattr(model_object, 'training_length', 30)

        # Calculate minimum sample length
        # Most models need input_chunk + output_chunk at minimum
        min_sample_length = input_chunk + output_chunk

        # For some models, training_length might be the critical parameter
        if hasattr(model_object, 'training_length') and training_length > min_sample_length:
            min_sample_length = training_length

        # Calculate minimum points for training set
        # We want at least MIN_TRAINING_SAMPLES samples
        min_train_points = max(
            min_sample_length,
            min_sample_length + (self.MIN_TRAINING_SAMPLES - 1) * output_chunk
        )

        if validation:
            # Calculate minimum points for validation set
            min_val_points = max(
                min_sample_length,
                min_sample_length + (self.MIN_VALIDATION_SAMPLES - 1) * output_chunk
            )

            # Calculate total required based on train_ratio
            # total * train_ratio >= min_train_points
            # total * (1 - train_ratio) >= min_val_points
            required_for_train = int(min_train_points / train_ratio)
            required_for_val = int(min_val_points / (1 - train_ratio))
            total_required = max(required_for_train, required_for_val)
        else:
            min_val_points = 0
            total_required = min_train_points

        # Add safety margin
        recommended = int(total_required * self.SAFETY_MARGIN_MULTIPLIER)

        return {
            'min_sample_length': min_sample_length,
            'min_train_points': min_train_points,
            'min_val_points': min_val_points,
            'total_required': total_required,
            'recommended': recommended,
            'input_chunk_length': input_chunk,
            'output_chunk_length': output_chunk,
            'training_length': training_length
        }

    def calculate_start_date(
        self,
        end_date: str,
        required_points: int,
        ticker: Optional[str] = None,
        buffer_days: int = 20
    ) -> str:
        """
        Calculate the start date needed to get required_points business days.

        Args:
            end_date: End date in 'YYYY-MM-DD' format
            required_points: Number of business days needed
            ticker: Stock ticker (optional, for future holiday calendar support)
            buffer_days: Extra days to account for holidays/weekends

        Returns:
            Start date in 'YYYY-MM-DD' format
        """
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        # Estimate calendar days needed
        # Business days are roughly 5/7 of calendar days
        estimated_calendar_days = int(required_points * 7 / 5) + buffer_days

        # Subtract from end date
        start_dt = end_dt - timedelta(days=estimated_calendar_days)

        return start_dt.strftime('%Y-%m-%d')

    def calculate_end_date(
        self,
        start_date: str,
        required_points: int,
        buffer_days: int = 20
    ) -> str:
        """
        Calculate the end date needed to get required_points from start_date.

        Args:
            start_date: Start date in 'YYYY-MM-DD' format
            required_points: Number of business days needed
            buffer_days: Extra days to account for holidays/weekends

        Returns:
            End date in 'YYYY-MM-DD' format
        """
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')

        # Estimate calendar days needed
        estimated_calendar_days = int(required_points * 7 / 5) + buffer_days

        # Add to start date
        end_dt = start_dt + timedelta(days=estimated_calendar_days)

        return end_dt.strftime('%Y-%m-%d')

    def auto_adjust_date_range(
        self,
        model_object,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        validation: bool = True,
        train_ratio: float = 0.8,
        ticker: Optional[str] = None,
        prefer_start_date: bool = True
    ) -> Dict[str, any]:
        """
        Automatically calculate optimal date range for model training.

        Args:
            model_object: Model instance with configuration
            start_date: Optional start date in 'YYYY-MM-DD' format
            end_date: Optional end date in 'YYYY-MM-DD' format
            validation: Whether validation is enabled
            train_ratio: Training data ratio
            ticker: Stock ticker symbol
            prefer_start_date: If True, keep start_date and adjust end_date;
                              If False, keep end_date and adjust start_date

        Returns:
            Dict with:
            {
                'start_date': Calculated start date,
                'end_date': Calculated end date,
                'required_points': Number of points needed,
                'estimated_points': Estimated points in range,
                'requirements': Detailed requirements dict,
                'adjusted': Whether dates were adjusted
            }
        """
        # Calculate requirements
        requirements = self.calculate_required_data_points(
            model_object, validation, train_ratio
        )

        # Use recommended points with safety margin
        required_points = requirements['recommended']

        # If both dates provided, validate them
        if start_date and end_date:
            # Calculate estimated business days
            estimated_points = self._estimate_business_days(start_date, end_date)

            if estimated_points >= requirements['total_required']:
                # Sufficient data, no adjustment needed
                return {
                    'start_date': start_date,
                    'end_date': end_date,
                    'required_points': requirements['total_required'],
                    'recommended_points': required_points,
                    'estimated_points': estimated_points,
                    'requirements': requirements,
                    'adjusted': False,
                    'sufficient': True
                }
            else:
                # Insufficient data, need to adjust
                if prefer_start_date:
                    # Keep start, extend end
                    new_end_date = self.calculate_end_date(start_date, required_points)
                    return {
                        'start_date': start_date,
                        'end_date': new_end_date,
                        'required_points': requirements['total_required'],
                        'recommended_points': required_points,
                        'estimated_points': required_points,
                        'requirements': requirements,
                        'adjusted': True,
                        'adjustment_type': 'extended_end_date',
                        'original_end_date': end_date,
                        'sufficient': False
                    }
                else:
                    # Keep end, extend start
                    new_start_date = self.calculate_start_date(end_date, required_points, ticker)
                    return {
                        'start_date': new_start_date,
                        'end_date': end_date,
                        'required_points': requirements['total_required'],
                        'recommended_points': required_points,
                        'estimated_points': required_points,
                        'requirements': requirements,
                        'adjusted': True,
                        'adjustment_type': 'extended_start_date',
                        'original_start_date': start_date,
                        'sufficient': False
                    }

        # If only start_date provided, calculate end_date
        elif start_date:
            new_end_date = self.calculate_end_date(start_date, required_points)
            return {
                'start_date': start_date,
                'end_date': new_end_date,
                'required_points': requirements['total_required'],
                'recommended_points': required_points,
                'estimated_points': required_points,
                'requirements': requirements,
                'adjusted': True,
                'adjustment_type': 'calculated_end_date',
                'sufficient': True
            }

        # If only end_date provided, calculate start_date
        elif end_date:
            new_start_date = self.calculate_start_date(end_date, required_points, ticker)
            return {
                'start_date': new_start_date,
                'end_date': end_date,
                'required_points': requirements['total_required'],
                'recommended_points': required_points,
                'estimated_points': required_points,
                'requirements': requirements,
                'adjusted': True,
                'adjustment_type': 'calculated_start_date',
                'sufficient': True
            }

        # If neither provided, use default (last 6 months)
        else:
            default_end = datetime.now().strftime('%Y-%m-%d')
            new_start_date = self.calculate_start_date(default_end, required_points, ticker)
            return {
                'start_date': new_start_date,
                'end_date': default_end,
                'required_points': requirements['total_required'],
                'recommended_points': required_points,
                'estimated_points': required_points,
                'requirements': requirements,
                'adjusted': True,
                'adjustment_type': 'default_range',
                'sufficient': True
            }

    def _estimate_business_days(self, start_date: str, end_date: str) -> int:
        """
        Estimate the number of business days between two dates.

        Args:
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format

        Returns:
            Estimated number of business days
        """
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        # Use numpy's busday_count for accurate calculation
        return int(np.busday_count(start_dt.date(), end_dt.date()))

    def get_recommendation_message(self, calculation_result: Dict) -> str:
        """
        Generate a human-readable recommendation message.

        Args:
            calculation_result: Result from auto_adjust_date_range()

        Returns:
            Formatted recommendation message
        """
        req = calculation_result['requirements']

        message = f"""
Date Range Recommendation:
========================

Model Requirements:
  - Input chunk length: {req['input_chunk_length']}
  - Output chunk length: {req['output_chunk_length']}
  - Minimum sample length: {req['min_sample_length']} points
  - Minimum training points: {req['min_train_points']} points
  - Minimum validation points: {req['min_val_points']} points
  - Total required: {req['total_required']} points
  - Recommended (with safety margin): {req['recommended']} points

Calculated Date Range:
  - Start Date: {calculation_result['start_date']}
  - End Date: {calculation_result['end_date']}
  - Estimated Data Points: {calculation_result['estimated_points']}
"""

        if calculation_result['adjusted']:
            message += f"\nNote: Date range was automatically adjusted ({calculation_result['adjustment_type']})"
            if 'original_start_date' in calculation_result:
                message += f"\n  Original start: {calculation_result['original_start_date']}"
            if 'original_end_date' in calculation_result:
                message += f"\n  Original end: {calculation_result['original_end_date']}"

        return message
