import logging
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from repositories.predict_solution_repository import PredictSolutionRepository
from repositories.model_repository import ModelRepository
from repositories.time_series_repository import TimeSeriesRepository
from repositories.model_capability_repository import ModelCapabilityRepository
from services.model_service import ModelService
from services.indicator_service import IndicatorService
from services.stock_data_sync_service import StockDataSyncService
from core.exceptions import EntityNotFoundException, SolutionTrainingException, IndicatorValidationException
from core.decorators import validate_input
from utils.date_range_calculator import DateRangeCalculator

logger = logging.getLogger(__name__)


class SolutionService:
    def __init__(self):
        self.solution_repo = PredictSolutionRepository()
        self.model_repo = ModelRepository()
        self.time_series_repo = TimeSeriesRepository()
        self.model_capability_repo = ModelCapabilityRepository()
        self.model_service = ModelService()
        self.indicator_service = IndicatorService()
        self.date_calculator = DateRangeCalculator()
    
    def adding_business_days(self, from_date: str, add_days: int) -> datetime:
        date_format = '%Y-%m-%d'
        business_days_to_add = add_days
        current_date = datetime.strptime(from_date, date_format)
        
        while business_days_to_add > 0:
            current_date += timedelta(days=1)
            weekday = current_date.weekday()
            if weekday >= 5:  # sunday = 6
                continue
            business_days_to_add -= 1
        
        return current_date
    
    def subtract_business_days(self, from_date: str, days: int) -> datetime:
        date_format = '%Y-%m-%d'
        business_days_to_subtract = days
        current_date = datetime.strptime(from_date, date_format)

        while business_days_to_subtract > 0:
            current_date += timedelta(days=-1)
            weekday = current_date.weekday()
            if weekday >= 5:  # sunday = 6
                continue
            business_days_to_subtract -= 1

        return current_date

    def solution_uses_indicators(self, solution_id: int) -> bool:
        """Check if solution uses technical indicators instead of time series"""
        validation = self.indicator_service.validate_solution_indicators(solution_id)
        return validation['is_valid']

    def _extract_training_predictions(self, model_object, ticker: str, start_date: str, end_date: str) -> List[Dict]:
        """
        Extract training predictions from the trained model using historical_forecasts

        Args:
            model_object: Trained model instance
            ticker: Stock symbol
            start_date: Training start date
            end_date: Training end date

        Returns:
            List of dicts with date, actual_price, and predicted_price
        """
        try:
            print("\n[EXTRACT PREDICTIONS] Starting prediction extraction...")

            # Get the target series (actual prices)
            target_series = model_object.target

            # Generate historical forecasts (predictions on training data)
            # Use the entire training period with start=0.8 to get validation predictions
            series_for_forecast = target_series[:-model_object.model.output_chunk_length] if len(target_series) > model_object.model.output_chunk_length else target_series

            predictions = model_object.model.historical_forecasts(
                series=series_for_forecast,
                past_covariates=model_object.past_multi if hasattr(model_object, 'past_multi') else None,
                future_covariates=model_object.future_multi if hasattr(model_object, 'future_multi') else None,
                start=0.8,  # Start predictions from 80% of data (validation period)
                retrain=False,
                verbose=False,
                forecast_horizon=model_object.model.output_chunk_length
            )

            print(f"[EXTRACT PREDICTIONS] Predictions generated, length: {len(predictions) if predictions else 0}")

            # Inverse transform predictions to original scale
            scaler = model_object.target_series.get_scaler()
            predictions_original_scale = scaler.inverse_transform(predictions)
            actual_original_scale = scaler.inverse_transform(target_series)

            # Get the price data to extract dates and volume
            price_df = self.indicator_service.advanced_indicators.get_price_data(ticker, start_date, end_date)
            price_df = price_df.reset_index()

            # Create a date->price mapping for quick lookup
            price_lookup = {}
            for _, row in price_df.iterrows():
                date_key = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']).split('T')[0]
                price_lookup[date_key] = {
                    'volume': float(row['volume']) if 'volume' in row and pd.notna(row['volume']) else None,
                    'open': float(row['open']) if 'open' in row and pd.notna(row['open']) else None,
                    'high': float(row['high']) if 'high' in row and pd.notna(row['high']) else None,
                    'low': float(row['low']) if 'low' in row and pd.notna(row['low']) else None
                }

            # Convert to list of dicts
            result = []

            # Add actual prices for entire training period
            actual_dates = actual_original_scale.time_index
            actual_values = actual_original_scale.values()

            for i, date in enumerate(actual_dates):
                date_key = date.strftime('%Y-%m-%d')
                price_data = price_lookup.get(date_key, {})

                result.append({
                    'date': date_key,
                    'actual_price': float(actual_values[i][0]),
                    'predicted_price': None,  # Will be filled for validation period
                    'volume': price_data.get('volume'),
                    'open': price_data.get('open'),
                    'high': price_data.get('high'),
                    'low': price_data.get('low')
                })

            # Fill in predicted values for validation period
            pred_dates = predictions_original_scale.time_index
            pred_values = predictions_original_scale.values()

            for i, pred_date in enumerate(pred_dates):
                # Find matching date in result
                for item in result:
                    if item['date'] == pred_date.strftime('%Y-%m-%d'):
                        item['predicted_price'] = float(pred_values[i][0])
                        item['validation_price'] = float(pred_values[i][0])  # Same as predicted for validation
                        break

            print(f"[EXTRACT PREDICTIONS] Total data points: {len(result)}")
            print(f"[EXTRACT PREDICTIONS] Points with predictions: {sum(1 for r in result if r['predicted_price'] is not None)}")
            print(f"[EXTRACT PREDICTIONS] Points with volume: {sum(1 for r in result if r.get('volume') is not None)}")

            return result

        except Exception as e:
            print(f"[EXTRACT PREDICTIONS] ERROR: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Return empty list if extraction fails
            return []

    def _normalize_date_format(self, date_str: str) -> str:
        """
        Normalize date string to YYYY-MM-DD format
        Handles both 'YYYY-MM-DD' and 'YYYY-MM-DDTHH:MM:SS' formats
        """
        if not date_str:
            return date_str

        # If it contains 'T', it's ISO format with time - extract date part only
        if 'T' in date_str:
            return date_str.split('T')[0]

        return date_str

    def _merge_predictions_with_indicators(self, predictions_data: List[Dict], indicators_data: Dict) -> List[Dict]:
        """
        Merge prediction data with indicator values by date

        Args:
            predictions_data: List of dicts with date, actual_price, predicted_price
            indicators_data: Dict of indicator type -> list of dicts with date and values

        Returns:
            Merged list of dicts with predictions and all indicators
        """
        try:
            print("\n[MERGE DATA] Starting merge...")
            print(f"[MERGE DATA] Predictions count: {len(predictions_data)}")
            print(f"[MERGE DATA] Indicator types: {list(indicators_data.keys())}")

            # Create a dictionary keyed by date for quick lookup
            merged = {}

            # First, add all prediction data
            for item in predictions_data:
                date_key = self._normalize_date_format(item['date'])
                merged[date_key] = {
                    'date': date_key,
                    'close': item['actual_price'],  # Use actual price as close
                    'actual_price': item['actual_price'],
                    'predicted_price': item.get('predicted_price'),
                    'validation_price': item.get('validation_price'),
                    # Preserve OHLCV data from predictions
                    'volume': item.get('volume'),
                    'open': item.get('open'),
                    'high': item.get('high'),
                    'low': item.get('low')
                }

            # Then, merge each indicator type
            for ind_type, ind_values in indicators_data.items():
                print(f"[MERGE DATA] Processing {ind_type} indicator...")
                for ind_item in ind_values:
                    # Normalize date format for matching
                    date_key = self._normalize_date_format(ind_item.get('date'))
                    if date_key in merged:
                        # Get all indicator values (excluding 'date')
                        for key, value in ind_item.items():
                            if key != 'date':
                                # Use lowercase field names for consistency
                                merged[date_key][key.lower()] = value
                    else:
                        # Date not in predictions, add indicator data only
                        merged[date_key] = {
                            'date': date_key,
                            **{k.lower(): v for k, v in ind_item.items() if k != 'date'}
                        }

            # Convert back to list and sort by date
            result = sorted(merged.values(), key=lambda x: x['date'])

            print(f"[MERGE DATA] Merged {len(result)} total points")
            if len(result) > 0:
                print(f"[MERGE DATA] First item (training period): {result[0]}")
                print(f"[MERGE DATA] Last item (validation period): {result[-1]}")

                # Count points with predictions and volume
                points_with_predictions = sum(1 for r in result if r.get('predicted_price') is not None)
                points_with_volume = sum(1 for r in result if r.get('volume') is not None)
                print(f"[MERGE DATA] Points with volume: {points_with_volume}")
                print(f"[MERGE DATA] Points with predictions: {points_with_predictions}/{len(result)}")

                # Show sample of items with predictions
                items_with_preds = [r for r in result if r.get('predicted_price') is not None]
                if len(items_with_preds) > 0:
                    print(f"[MERGE DATA] Sample item WITH prediction: {items_with_preds[0]}")
                else:
                    print(f"[MERGE DATA] ⚠️ WARNING: NO items have predictions!")

            return result

        except Exception as e:
            print(f"[MERGE DATA] ERROR: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Return predictions only if merge fails
            return predictions_data

    def _prepare_indicator_data_for_training(self, solution_id: int, ticker: str,
                                            start_date: str, end_date: str,
                                            model_object) -> None:
        """Prepare and load indicator-based features for model training"""
        # Get solution indicators with covariate types
        solution_indicators = self.indicator_service.get_solution_indicators(solution_id)

        # Calculate all indicators for the solution
        calculated_indicators = self.indicator_service.calculate_solution_indicators({
            'solution_id': solution_id,
            'symbol': ticker,
            'start_date': start_date,
            'end_date': end_date
        })

        # Build DataFrame from indicators
        indicator_df = self.indicator_service.build_indicator_dataframe(calculated_indicators)

        if indicator_df.empty:
            raise ValueError("No indicator data could be calculated")

        # Fetch close price data and align it with indicator dates
        # This ensures target and covariates have the same date index
        price_df = self.indicator_service.advanced_indicators.get_price_data(ticker, start_date, end_date)

        # Reset index to have 'date' as a column for merging
        price_df = price_df.reset_index()
        price_df = price_df.rename(columns={'date': 'time'})  # Align column naming
        price_df['date'] = pd.to_datetime(price_df['time'])

        # Merge close price with indicator dates (use indicator dates as master)
        indicator_df['date'] = pd.to_datetime(indicator_df['date'])
        combined_df = indicator_df.merge(
            price_df[['date', 'close']],
            on='date',
            how='left'
        )

        # Forward fill any missing close prices (should be minimal if dates align)
        combined_df['close'] = combined_df['close'].ffill().bfill()

        print(f"\n[DATA ALIGNMENT] Combined DataFrame shape: {combined_df.shape}")
        print(f"[DATA ALIGNMENT] Columns: {list(combined_df.columns)}")
        print(f"[DATA ALIGNMENT] Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
        print(f"[DATA ALIGNMENT] Close price null count: {combined_df['close'].isna().sum()}")

        # Add each indicator column as a feature to the model with proper covariate type
        for col in combined_df.columns:
            if col == 'date':
                continue
            elif col == 'close':
                # Add close as target - will be set after all fields are added
                model_object.add_field_from_dataframe(col, combined_df[['date', col]])
            else:
                # Add indicator as a field to the model
                model_object.add_field_from_dataframe(col, combined_df[['date', col]])

                # Get the covariate type for this indicator category
                if col in solution_indicators and solution_indicators[col]:
                    covariate_type = solution_indicators[col].get('covariate_type', 'past')

                    if covariate_type == 'past':
                        model_object.add_past_covariate(col)
                    elif covariate_type == 'future':
                        model_object.add_future_covariate(col)
                    elif covariate_type == 'both':
                        model_object.add_past_covariate(col)
                        model_object.add_future_covariate(col)
                else:
                    # Default to past covariate if not specified
                    model_object.add_past_covariate(col)

        # Set the target series to close price
        model_object.set_target_series('close')

    @validate_input()
    def train_solution(self, params: Dict) -> Dict:
        try:
            solution_id = params['id']
            start_date = params.get('start_date')
            end_date = params.get('end_date')
            validation = params.get('validation', False)
            train_ratio = params.get('train_ratio', 0.8)
            auto_adjust_dates = params.get('auto_adjust_dates', True)  # New parameter

            # Get solution details
            solution = self.solution_repo.get_solution_by_id(solution_id)
            if not solution:
                raise EntityNotFoundException("Solution", str(solution_id))

            # Set ticker early for pre-training sync
            ticker = solution['ticker']

            # PRE-TRAINING: Try to update with latest stock data
            # Graceful: continues with existing data if update fails
            try:
                sync_service = StockDataSyncService()
                sync_result = sync_service.update_latest_data(ticker)
                if sync_result.status == 'success':
                    if sync_result.records_added > 0:
                        logger.info(f"Pre-training sync: Updated {ticker} with {sync_result.records_added} new records")
                    else:
                        logger.info(f"Pre-training sync: {ticker} already up to date")
                elif sync_result.status == 'skipped':
                    logger.info(f"Pre-training sync: {ticker} skipped - {sync_result.message}")
                else:
                    logger.warning(f"Pre-training sync warning for {ticker}: {sync_result.message}")
            except Exception as sync_error:
                # Graceful degradation - log warning but continue with existing data
                logger.warning(f"Pre-training sync failed for {ticker}: {str(sync_error)}. Continuing with existing data.")

            # Get model details
            model_db = self.model_repo.get_model_by_id(solution['model_id'])
            model_type = model_db['model_type']
            model_name = model_db['model_name']

            # Get model object early to calculate date ranges
            model_object = self.model_service.get_model_by_id_with_file(
                solution['model_id'], model_name, model_type
            )
            model_object.set_validation(validation)
            model_object.set_train_ratio(train_ratio)

            # Set ticker for model (already set earlier for pre-training sync)
            model_object.set_ticker(ticker=ticker)

            # AUTO-CALCULATE DATE RANGE if enabled
            if auto_adjust_dates:
                date_range_result = self.date_calculator.auto_adjust_date_range(
                    model_object=model_object,
                    start_date=start_date,
                    end_date=end_date,
                    validation=validation,
                    train_ratio=train_ratio,
                    ticker=ticker,
                    prefer_start_date=True if start_date else False
                )

                # Use calculated dates
                start_date = date_range_result['start_date']
                end_date = date_range_result['end_date']

                # Log the adjustment
                if date_range_result['adjusted']:
                    print("\n========== DATE RANGE AUTO-ADJUSTMENT ==========")
                    print(f"Adjustment Type: {date_range_result['adjustment_type']}")
                    if 'original_start_date' in date_range_result:
                        print(f"Original Start: {date_range_result['original_start_date']} → New: {start_date}")
                    if 'original_end_date' in date_range_result:
                        print(f"Original End: {date_range_result['original_end_date']} → New: {end_date}")
                    print(f"Required Points: {date_range_result['required_points']}")
                    print(f"Recommended Points: {date_range_result['recommended_points']}")
                    print(f"Estimated Points: {date_range_result['estimated_points']}")
                    print("=" * 50)

            # Update training status with final dates
            self.solution_repo.update_training_solution(solution_id, start_date, end_date)

            # Check if solution uses indicators or traditional time series
            uses_indicators = self.solution_uses_indicators(solution_id)

            print("\n========== DEBUG: train_solution ==========")
            print(f"Solution ID: {solution_id}")
            print(f"Ticker: {ticker}")
            print(f"Model: {model_name} ({model_type})")
            print(f"Uses Indicators: {uses_indicators}")
            print(f"Start Date: {start_date}, End Date: {end_date}")
            print(f"Validation: {validation}, Train Ratio: {train_ratio}")

            if uses_indicators:
                # NEW APPROACH: Use technical indicators
                print("\n[STEP 1] Preparing indicator data...")
                self._prepare_indicator_data_for_training(
                    solution_id, ticker, start_date, end_date, model_object
                )
                print(f"[STEP 1] Complete - Indicators loaded")
                print(f"  - Past covariates: {model_object.past_covariates}")
                print(f"  - Future covariates: {model_object.future_covariates}")
                print(f"  - Target series: {model_object.target_series.field_name if hasattr(model_object, 'target_series') else 'Not set'}")
            else:
                # LEGACY APPROACH: Use time series
                print("\n[STEP 1] Preparing legacy time series data...")
                # Prepare time series indices
                idx = [{"name": "target", "value": str(solution['target'])}]

                # Add past covariates if enabled
                if model_db['past_covariate']:
                    past_idx = solution['past_covariate']
                    for past_id in past_idx:
                        idx.append({"name": "past", "value": str(past_id)})

                # Add future covariates if enabled
                if model_db['future_covariate']:
                    future_idx = solution['future_covariate']
                    for future_id in future_idx:
                        idx.append({"name": "future", "value": str(future_id)})

                # Process time series data
                for series_info in idx:
                    series = self.time_series_repo.get_series_by_id(int(series_info["value"]))
                    if not series:
                        raise EntityNotFoundException("Time Series", series_info["value"])

                    name = series['series_type_name']
                    model_object.add_field(name, start_date, end_date)

                    if series_info["name"] == "target":
                        model_object.set_target_series(name)
                    elif series_info["name"] == "past":
                        model_object.add_past_covariate(name)
                    elif series_info["name"] == "future":
                        model_object.add_future_covariate(name)

                print(f"[STEP 1] Complete - Time series loaded")

            # Train model
            print("\n[STEP 2] Preprocessing data...")
            model_object.preprocess_data()
            print(f"[STEP 2] Complete - Data preprocessed")
            print(f"  - Train target shape: {model_object.train_target.values().shape if hasattr(model_object, 'train_target') else 'N/A'}")
            if hasattr(model_object, 'val_target'):
                print(f"  - Val target shape: {model_object.val_target.values().shape if model_object.val_target else 'No validation'}")
            if hasattr(model_object, 'past_train_multi'):
                print(f"  - Past covariates shape: {model_object.past_train_multi.values().shape if model_object.past_train_multi else 'None'}")
            if hasattr(model_object, 'future_train_multi'):
                print(f"  - Future covariates shape: {model_object.future_train_multi.values().shape if model_object.future_train_multi else 'None'}")

            print("\n[STEP 3] Training model...")
            try:
                trained_model_path = model_object.train(solution['model_id'])
                print(f"[STEP 3] Complete - Model trained and saved to: {trained_model_path}")
            except ValueError as train_error:
                error_msg = str(train_error)

                # Check if this is a "series too short" error
                if "too short to extract even a single sample" in error_msg and "Expected min length" in error_msg:
                    print(f"[STEP 3] ERROR: Insufficient data for model training")

                    # Extract expected and received lengths from error message
                    import re
                    expected_match = re.search(r'Expected min length: `(\d+)`', error_msg)
                    received_match = re.search(r'received max length: `(\d+)`', error_msg)

                    expected_length = int(expected_match.group(1)) if expected_match else 'unknown'
                    received_length = int(received_match.group(1)) if received_match else 'unknown'

                    # Get model parameters for suggestions
                    training_length = getattr(model_object, 'training_length', 'unknown')
                    input_chunk = getattr(model_object, 'input_chunk_length', 'unknown')

                    # Build helpful suggestions
                    suggestions = [
                        f"Current data length: {received_length} points",
                        f"Required minimum: {expected_length} points",
                        f"Current model parameters - training_length: {training_length}, input_chunk_length: {input_chunk}",
                        "",
                        "SOLUTIONS:",
                        "1. Reduce 'training_length' parameter (e.g., from 30 to 10-15)",
                        "2. Reduce 'input_chunk_length' parameter (e.g., from 14 to 7)",
                        "3. Extend your date range to collect more historical data",
                        "4. Disable validation mode to use all available data for training",
                        "",
                        f"Recommended settings for {received_length} data points:",
                        f"  - training_length: {max(10, received_length // 3)}",
                        f"  - input_chunk_length: {max(5, received_length // 4)}",
                        f"  - validation: false (to use all {received_length} points for training)"
                    ]

                    raise SolutionTrainingException(
                        solution_id=str(solution_id),
                        message=f"Insufficient training data: {error_msg}",
                        suggestions=suggestions
                    )
                else:
                    # Re-raise other ValueError types
                    print(f"[STEP 3] ERROR during training: {str(train_error)}")
                    print(f"  Error type: {type(train_error).__name__}")
                    import traceback
                    print(f"  Traceback:\n{traceback.format_exc()}")
                    raise
            except Exception as train_error:
                print(f"[STEP 3] ERROR during training: {str(train_error)}")
                print(f"  Error type: {type(train_error).__name__}")
                import traceback
                print(f"  Traceback:\n{traceback.format_exc()}")
                raise

            # Evaluate model
            print("\n[STEP 4] Evaluating model...")
            try:
                rmse = model_object.evaluate_model()
                print(f"[STEP 4] Complete - RMSE: {rmse}")
            except Exception as eval_error:
                print(f"[STEP 4] ERROR during evaluation: {str(eval_error)}")
                print(f"  Error type: {type(eval_error).__name__}")
                import traceback
                print(f"  Traceback:\n{traceback.format_exc()}")
                raise

            # Update model status to 'trained' in the database
            print("\n[STEP 5] Updating model status to 'trained'...")
            try:
                self.model_service.update_training_status(
                    solution['model_id'],
                    'trained',
                    {'rmse': rmse}
                )
                # CRITICAL: Also update the file_path with the actual trained model location
                # This ensures the model can be loaded later for prediction
                if trained_model_path:
                    self.model_service.unified_service.instance_repo.update_model_instance(
                        solution['model_id'],
                        file_path=trained_model_path
                    )
                    print(f"[STEP 5] Complete - Model status updated, file_path: {trained_model_path}")
                else:
                    print(f"[STEP 5] Complete - Model status updated")
            except Exception as status_error:
                print(f"[STEP 5] WARNING: Failed to update model status: {str(status_error)}")
                # Don't fail the training if status update fails

            # Extract training predictions
            print("\n[STEP 6] Extracting training predictions...")
            try:
                predictions_data = self._extract_training_predictions(
                    model_object,
                    solution['ticker'],
                    start_date,
                    end_date
                )
                print(f"[STEP 6] Complete - Extracted {len(predictions_data)} prediction points")
            except Exception as pred_error:
                print(f"[STEP 6] WARNING: Failed to extract predictions: {str(pred_error)}")
                predictions_data = []

            # Get calculated indicators if solution uses them
            print("\n[STEP 7] Fetching indicator values...")
            indicators_data = {}
            try:
                if self.solution_uses_indicators(solution_id):
                    calculated_indicators = self.indicator_service.calculate_solution_indicators({
                        'solution_id': solution_id,
                        'symbol': solution['ticker'],
                        'start_date': start_date,
                        'end_date': end_date
                    })

                    # Convert indicator data to flat structure for merging
                    for ind_type, ind_info in calculated_indicators.items():
                        if ind_info and 'data' in ind_info:
                            indicators_data[ind_type] = ind_info['data']

                    print(f"[STEP 7] Complete - Fetched {len(indicators_data)} indicator types")
                else:
                    print(f"[STEP 7] Solution does not use indicators, skipping")
            except Exception as ind_error:
                print(f"[STEP 7] WARNING: Failed to fetch indicators: {str(ind_error)}")

            # Merge predictions with indicators
            print("\n[STEP 8] Merging predictions with indicators...")
            merged_data = self._merge_predictions_with_indicators(predictions_data, indicators_data)
            print(f"[STEP 8] Complete - Merged data has {len(merged_data)} points")

            # Calculate prediction date range based on training end date and model parameters
            print("\n[STEP 9] Calculating prediction date range...")
            output_chunk_length = getattr(model_object, 'output_chunk_length', 10)

            # Prediction start date = training end date + 1 business day
            prediction_start_date = self.adding_business_days(end_date, 1)
            # Prediction end date = prediction start date + output_chunk_length business days
            prediction_end_date = self.adding_business_days(
                prediction_start_date.strftime('%Y-%m-%d'),
                output_chunk_length - 1  # -1 because start date counts as day 1
            )

            prediction_dates = {
                'prediction_start_date': prediction_start_date.strftime('%Y-%m-%d'),
                'prediction_end_date': prediction_end_date.strftime('%Y-%m-%d'),
                'output_chunk_length': output_chunk_length,
                'training_end_date': end_date
            }
            print(f"[STEP 9] Complete - Prediction range: {prediction_dates['prediction_start_date']} to {prediction_dates['prediction_end_date']}")

            print("\n========== SUCCESS: Training completed ==========\n")

            return {
                **solution,
                'rmse': rmse,
                'training_status': 'completed',
                'predictions': merged_data,  # Include predictions with indicators
                'prediction_dates': prediction_dates,  # Include auto-calculated prediction dates
                'model_id': solution['model_id']  # Include model_id for loading trained model
            }
            
        except IndicatorValidationException as e:
            # Pass through indicator validation exceptions with suggestions
            raise SolutionTrainingException(
                solution_id=str(solution_id),
                message=str(e),
                suggestions=e.suggestions
            )
        except Exception as e:
            print(str(e))
            raise SolutionTrainingException(str(solution_id), str(e))
    
    @validate_input()
    def predict_solution(self, params: Dict) -> Dict:
        try:
            solution_id = params['id']
            predict_start_date = params['start_date']
            predict_end_date = params['end_date']

            print("\n========== DEBUG: predict_solution ==========")
            print(f"Solution ID: {solution_id}")
            print(f"Prediction period: {predict_start_date} to {predict_end_date}")

            # Get solution details
            solution = self.solution_repo.get_solution_by_id(solution_id)
            if not solution:
                raise EntityNotFoundException("Solution", str(solution_id))

            # Get model details
            model_db = self.model_repo.get_model_by_id(solution['model_id'])
            model_type = model_db['model_type']
            model_name = model_db['model_name']

            print(f"Model ID: {solution['model_id']}")
            print(f"Model: {model_name} ({model_type})")
            print(f"Ticker: {solution['ticker']}")

            # Get model object
            print("\n[STEP 1] Loading model...")
            model_object = self.model_service.get_model_by_id_with_file(
                solution['model_id'], model_name, model_type
            )
            print(f"[STEP 1] Complete - Model loaded")

            # Set ticker
            ticker = solution['ticker']
            model_object.set_ticker(ticker=ticker)

            # Calculate prediction length
            day_num = np.busday_count(predict_start_date, predict_end_date)

            # Get the model's maximum prediction length (output_chunk_length)
            max_prediction_length = model_object.get_max_prediction_length()
            print(f"Model max prediction length (output_chunk_length): {max_prediction_length}")

            # Cap prediction length to model's maximum
            if day_num > max_prediction_length:
                print(f"[AUTO-ADJUST] Requested {day_num} days exceeds model max {max_prediction_length}. Capping to {max_prediction_length}.")
                predict_length = max_prediction_length
            else:
                predict_length = day_num if day_num > 0 else max_prediction_length

            # Use the larger of day_num and input_chunk_length for data preparation
            length = max(day_num, model_object.get_chunk_length()) if model_object.get_chunk_length() else day_num

            # Adjust date range for data requirements
            adjusted_start = self.subtract_business_days(predict_start_date, length)
            adjusted_end = self.adding_business_days(predict_end_date, length)

            # Check if solution uses indicators or traditional time series
            uses_indicators = self.solution_uses_indicators(solution_id)

            print(f"\n[STEP 2] Preparing data for prediction...")
            print(f"Uses Indicators: {uses_indicators}")
            print(f"Adjusted date range: {adjusted_start.strftime('%Y-%m-%d')} to {adjusted_end.strftime('%Y-%m-%d')}")

            if uses_indicators:
                # NEW APPROACH: Use technical indicators for prediction
                print("[STEP 2] Loading indicator data...")
                self._prepare_indicator_data_for_training(
                    solution_id, ticker,
                    adjusted_start.strftime('%Y-%m-%d'),
                    adjusted_end.strftime('%Y-%m-%d'),
                    model_object
                )
                print(f"[STEP 2] Complete - Indicator data loaded")
            else:
                # LEGACY APPROACH: Use time series for prediction
                # Prepare time series indices
                idx = [{"name": "target", "value": str(solution['target'])}]

                # Add past covariates if enabled
                if model_db['past_covariate']:
                    past_idx = solution['past_covariate']
                    for past_id in past_idx:
                        idx.append({"name": "past", "value": str(past_id)})

                # Add future covariates if enabled
                if model_db['future_covariate']:
                    future_idx = solution['future_covariate']
                    for future_id in future_idx:
                        idx.append({"name": "future", "value": str(future_id)})

                # Process time series data for prediction
                for series_info in idx:
                    series = self.time_series_repo.get_series_by_id(int(series_info["value"]))
                    if not series:
                        raise EntityNotFoundException("Time Series", series_info["value"])

                    name = series['series_type_name']

                    model_object.add_field(name, adjusted_start.strftime('%Y-%m-%d'),
                                         adjusted_end.strftime('%Y-%m-%d'))

                    if series_info["name"] == "target":
                        model_object.set_target_series(name)
                    elif series_info["name"] == "past":
                        model_object.add_past_covariate(name)
                    elif series_info["name"] == "future":
                        model_object.add_future_covariate(name)

                print(f"[STEP 2] Complete - Time series data loaded")

            # Get actual data
            print("\n[STEP 3] Extracting actual data...")
            target_series = model_object.target_series
            time_index = target_series.time_series.time_index
            values = target_series.time_series.values(copy=True)

            actual_json = []
            for i in range(len(time_index)):
                json_obj = {
                    'tradingdate': time_index[i],
                    'close': values[i][0]
                }
                actual_json.append(json_obj)
            print(f"[STEP 3] Complete - {len(actual_json)} actual data points extracted")

            # Generate predictions
            print("\n[STEP 4] Generating predictions...")
            print(f"Prediction start: {predict_start_date}, Length: {predict_length}")
            predict_json = model_object.predict(predict_start_date, predict_length)
            print(f"[STEP 4] Complete - {len(predict_json)} predictions generated")

            # Update train_status to 'predicted'
            print("\n[STEP 5] Updating solution status to 'predicted'...")
            self.solution_repo.update_train_status(solution_id, 'predicted')
            print(f"[STEP 5] Complete - Solution status updated to 'predicted'")

            print("\n========== SUCCESS: Prediction completed ==========\n")

            return {
                'actual': actual_json,
                'predict': predict_json,
                'solution_id': solution_id,
                'ticker': ticker,
                'train_status': 'predicted'
            }
            
        except Exception as e:
            raise SolutionTrainingException(str(solution_id), f"Prediction failed: {str(e)}")
    
    def get_all_solutions(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        Get all solutions, optionally filtered by user.

        Args:
            user_id: Optional user filter

        Returns:
            List of solution information
        """
        return self.solution_repo.get_solutions(user_id)

    def get_solutions_by_user(self, user_id: str) -> List[Dict]:
        """
        Get all solutions created by a specific user.

        Args:
            user_id: User identifier

        Returns:
            List of user's solutions
        """
        return self.solution_repo.get_solutions(user_id)

    def get_solution_by_id(self, solution_id: int) -> Dict:
        solution = self.solution_repo.get_solution_by_id(solution_id)

        # Check if solution has been trained
        # Support both old schema (solution_status=1) and new schema (train_status in ['trained', 'predicted'])
        is_trained = False
        if solution:
            train_status = solution.get('train_status')
            solution_status = solution.get('solution_status')
            end_training_date = solution.get('end_training_date')

            # Check if trained using either schema
            if train_status in ['trained', 'predicted']:
                is_trained = True
            elif solution_status == 1:
                is_trained = True

            print(f"[DEBUG get_solution_by_id] solution_id={solution_id}, train_status={train_status}, solution_status={solution_status}, end_training_date={end_training_date}, is_trained={is_trained}")

        # If solution has been trained and has end_training_date, calculate prediction dates
        if solution and solution.get('end_training_date') and is_trained:
            try:
                # Get model to retrieve output_chunk_length
                model_id = solution.get('model_id')
                print(f"[DEBUG] model_id={model_id}")

                if model_id:
                    model_db = self.model_repo.get_model_by_id(model_id)
                    model_type = model_db.get('model_type', '')
                    print(f"[DEBUG] model_type={model_type}")

                    # Get output_chunk_length from model config or use defaults
                    config_json = model_db.get('config_json', {})
                    if isinstance(config_json, str):
                        import json
                        config_json = json.loads(config_json)

                    # Default output_chunk_length based on model type
                    default_output_chunk = 10
                    if model_type == 'TFT':
                        default_output_chunk = 12
                    elif model_type in ['RandomForest', 'XGBoost', 'CatBoost', 'LightGBM']:
                        default_output_chunk = 1

                    output_chunk_length = config_json.get('output_chunk_length', default_output_chunk)
                    print(f"[DEBUG] output_chunk_length={output_chunk_length}")

                    # Calculate prediction dates
                    end_training_date = solution['end_training_date']
                    if hasattr(end_training_date, 'strftime'):
                        end_training_date = end_training_date.strftime('%Y-%m-%d')
                    else:
                        end_training_date = str(end_training_date)

                    print(f"[DEBUG] end_training_date={end_training_date}")

                    prediction_start_date = self.adding_business_days(end_training_date, 1)
                    prediction_end_date = self.adding_business_days(
                        prediction_start_date.strftime('%Y-%m-%d'),
                        output_chunk_length - 1
                    )

                    solution['prediction_dates'] = {
                        'prediction_start_date': prediction_start_date.strftime('%Y-%m-%d'),
                        'prediction_end_date': prediction_end_date.strftime('%Y-%m-%d'),
                        'output_chunk_length': output_chunk_length,
                        'training_end_date': end_training_date
                    }
                    print(f"[DEBUG] prediction_dates={solution['prediction_dates']}")

            except Exception as e:
                print(f"[WARNING] Could not calculate prediction dates: {str(e)}")
                import traceback
                traceback.print_exc()
                # Don't fail if prediction date calculation fails

        return solution

    def create_solution(self, data: Dict) -> int:
        return self.solution_repo.create_predict_solution(data)

    def update_solution(self, data: Dict) -> bool:
        return self.solution_repo.update_predict_solution(data)

    def delete_solution(self, solution_id: int) -> bool:
        return self.solution_repo.delete_solution_by_id(solution_id)

    def update_train_status(self, solution_id: int, train_status: str) -> bool:
        """
        Update the training status of a solution.

        Args:
            solution_id: Solution ID
            train_status: One of 'not_trained', 'trained', 'predicted'

        Returns:
            True if updated successfully
        """
        return self.solution_repo.update_train_status(solution_id, train_status)

    def get_predict_models(self) -> List[Dict]:
        return self.solution_repo.get_predict_models()

    def get_predict_covariates(self) -> List[Dict]:
        return self.solution_repo.get_predict_covariates()

    def calculate_recommended_date_range(self, params: Dict) -> Dict:
        """
        Calculate recommended date range for model training.

        Args:
            params: Dict with:
                - model_id: Model ID
                - start_date: Optional start date
                - end_date: Optional end date
                - validation: Whether validation is enabled
                - train_ratio: Training data ratio
                - ticker: Stock ticker

        Returns:
            Dict with recommended dates and requirements
        """
        try:
            from datetime import datetime, timedelta

            model_id = params['model_id']
            start_date = params.get('start_date')
            end_date = params.get('end_date')
            validation = params.get('validation', True)
            train_ratio = params.get('train_ratio', 0.8)
            ticker = params.get('ticker')

            # Get model details from database
            model_db = self.model_repo.get_model_by_id(model_id)
            model_type = model_db['model_type']
            model_name = model_db['model_name']

            # Check if model supports future covariates
            try:
                model_capabilities = self.model_capability_repo.get_capabilities_by_model_type(model_type)
                supports_future_covariates = model_capabilities.get('supports_future_covariates', False) if model_capabilities else False
            except EntityNotFoundException:
                # Model type not found in capabilities table, assume no future covariate support
                model_capabilities = None
                supports_future_covariates = False

            # For date range calculation, we don't need to create a full model instance
            # We can create a mock object with just the required parameters
            class MockModel:
                def __init__(self, model_type):
                    # Set default parameters based on model type
                    # These match the defaults in each model class
                    if model_type == 'TFT':
                        self.input_chunk_length = 24
                        self.output_chunk_length = 12
                    elif model_type in ['BlockRNN', 'DLinear', 'NLinear', 'TCN', 'Transformer', 'NBeats', 'NHits', 'RNN']:
                        self.input_chunk_length = 14
                        self.output_chunk_length = 10
                    elif model_type in ['RandomForest', 'XGBoost', 'LightGBM', 'CatBoost']:
                        self.input_chunk_length = 14
                        self.output_chunk_length = 10
                    else:
                        # Default fallback
                        self.input_chunk_length = 14
                        self.output_chunk_length = 10

                    # Optional parameters
                    self.training_length = getattr(self, 'input_chunk_length', 14) + getattr(self, 'output_chunk_length', 10)

                def set_validation(self, val):
                    pass

                def set_train_ratio(self, ratio):
                    pass

                def set_ticker(self, ticker):
                    pass

            model_object = MockModel(model_type)

            # For models with future covariates, adjust end_date if needed
            # The end_date must be at least output_chunk_length days before today
            # to ensure we have future covariate data for prediction
            original_end_date = end_date
            future_covariate_constraint_applied = False

            if supports_future_covariates and end_date:
                today = datetime.now().date()
                requested_end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

                # Calculate maximum allowed end_date for models with future covariates
                # We need at least output_chunk_length days of future data for prediction
                max_end_date = today - timedelta(days=model_object.output_chunk_length)

                if requested_end_date > max_end_date:
                    end_date = max_end_date.strftime('%Y-%m-%d')
                    future_covariate_constraint_applied = True
                    print(f"[INFO] Adjusted end_date from {original_end_date} to {end_date} due to future covariate constraint (need {model_object.output_chunk_length} days of future data)")

            # Calculate date range
            result = self.date_calculator.auto_adjust_date_range(
                model_object=model_object,
                start_date=start_date,
                end_date=end_date,
                validation=validation,
                train_ratio=train_ratio,
                ticker=ticker,
                prefer_start_date=True if start_date else False
            )

            # Add future covariate information to result
            result['supports_future_covariates'] = supports_future_covariates
            result['future_covariate_constraint_applied'] = future_covariate_constraint_applied
            if future_covariate_constraint_applied:
                result['original_requested_end_date'] = original_end_date
                result['future_covariate_days_needed'] = model_object.output_chunk_length
                result['max_end_date'] = (datetime.now().date() - timedelta(days=model_object.output_chunk_length)).strftime('%Y-%m-%d')

            # Add recommendation message
            result['message'] = self.date_calculator.get_recommendation_message(result)

            return result

        except Exception as e:
            import traceback
            print(f"[ERROR] calculate_recommended_date_range failed: {str(e)}")
            print(f"Traceback:\n{traceback.format_exc()}")
            raise Exception(f"Failed to calculate date range: {str(e)}")