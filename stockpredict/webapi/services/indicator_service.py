"""
Indicator Service
Manages technical indicators for prediction solutions with database integration.
"""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from services.advanced_technical_indicators import AdvancedTechnicalIndicators, IndicatorCategory
from repositories.indicator_repository import IndicatorRepository
from core.exceptions import EntityNotFoundException, ValidationException, IndicatorValidationException
from core.decorators import validate_input


class IndicatorService:
    def __init__(self):
        self.indicator_repo = IndicatorRepository()
        self.advanced_indicators = AdvancedTechnicalIndicators()

        # Mapping from full indicator names (database) to short codes (calculation)
        self.indicator_name_mapping = {
            # Trend - Moving Averages
            'SMA (5)': 'SMA', 'SMA (10)': 'SMA', 'SMA (20)': 'SMA',
            'SMA (50)': 'SMA', 'SMA (100)': 'SMA', 'SMA (200)': 'SMA',
            'EMA (5)': 'EMA', 'EMA (10)': 'EMA', 'EMA (12)': 'EMA',
            'EMA (20)': 'EMA', 'EMA (26)': 'EMA', 'EMA (50)': 'EMA',
            'WMA (10)': 'WMA', 'WMA (20)': 'WMA',
            'DEMA (20)': 'DEMA', 'TEMA (20)': 'TEMA',
            'Simple Moving Average': 'SMA', 'Exponential Moving Average': 'EMA',
            'Weighted Moving Average': 'WMA', 'Moving Average': 'SMA',

            # Trend - Direction
            'Parabolic SAR': 'PSAR', 'Supertrend': 'SUPERTREND',
            'Ichimoku Cloud': 'ICHIMOKU', 'ADX (14)': 'ADX',
            'Aroon (25)': 'AROON', 'Vortex Indicator': 'VORTEX',
            'Average Directional Index': 'ADX', 'MACD': 'MACD',
            'MACD (12,26,9)': 'MACD',

            # Momentum
            'RSI (7)': 'RSI', 'RSI (14)': 'RSI', 'RSI (21)': 'RSI',
            'Relative Strength Index': 'RSI',
            'Stochastic (14,3,3)': 'STOCH', 'Stochastic Oscillator': 'STOCH',
            'Stochastic RSI': 'STOCH_RSI',
            'CCI (20)': 'CCI', 'Commodity Channel Index': 'CCI',
            'Momentum (10)': 'MOM',
            'Rate of Change (12)': 'ROC', 'Rate of Change': 'ROC',
            'Williams %R (14)': 'WILLIAMS_R', 'Williams %R': 'WILLIAMS_R',
            'True Strength Index': 'TSI',
            'Ultimate Oscillator': 'UO',
            'Awesome Oscillator': 'AO',

            # Volatility
            'Bollinger Bands (20,2)': 'BB', 'Bollinger Bands (20,3)': 'BB',
            'Bollinger Bands': 'BB',
            'ATR (14)': 'ATR', 'ATR (20)': 'ATR', 'Average True Range': 'ATR',
            'Keltner Channel': 'KELTNER',
            'Donchian Channel (20)': 'DONCHIAN', 'Donchian Channel': 'DONCHIAN',
            'Standard Deviation': 'STDDEV',
            'Historical Volatility': 'HV',

            # Volume
            'Volume': 'VOLUME',
            'On Balance Volume': 'OBV',
            'VWAP': 'VWAP', 'Volume Weighted Average Price': 'VWAP',
            'Money Flow Index (14)': 'MFI', 'Money Flow Index': 'MFI',
            'A/D Line': 'AD', 'Accumulation/Distribution Line': 'AD',
            'Chaikin Money Flow': 'CMF',
            'Chaikin Oscillator': 'CHO',
            'Volume Oscillator': 'VOSC',
            'Ease of Movement': 'EOM',
            'Force Index': 'FI',
            'Negative Volume Index': 'NVI',
            'Positive Volume Index': 'PVI',
            'Volume MA': 'Volume_MA', 'Volume Moving Average': 'Volume_MA',

            # Support & Resistance
            'Pivot Points': 'PIVOT',
            'Fibonacci Retracement': 'FIB_RET',
            'Fibonacci Extension': 'FIB_EXT',

            # Price Transform
            'Heikin Ashi': 'HEIKIN_ASHI',
            'Renko': 'RENKO',
            'Typical Price': 'TP',
            'Median Price': 'MP',
            'Weighted Close': 'WC',

            # Bill Williams
            'Alligator': 'ALLIGATOR',
            'Fractals': 'FRACTALS',
            'Gator Oscillator': 'GATOR',
            'Market Facilitation Index': 'MFI_BW',
            'Accelerator Oscillator': 'AC',
        }

    def _get_indicator_code(self, indicator_name: str) -> str:
        """Convert full indicator name to short code for calculation"""
        # Return mapped code or original name if no mapping exists
        return self.indicator_name_mapping.get(indicator_name, indicator_name)

    def get_all_indicators(self) -> Dict[str, List[Dict]]:
        """Get all technical indicators grouped by category"""
        return self.indicator_repo.get_all_indicators_by_category()

    def get_indicators_by_type(self, indicator_type: str) -> List[Dict]:
        """Get indicators filtered by type"""
        valid_types = ['trend', 'momentum', 'volatility', 'volume', 'support_resistance', 'price_transform', 'bill_williams']
        if indicator_type not in valid_types:
            raise ValidationException(f"Invalid indicator type. Must be one of: {', '.join(valid_types)}")

        return self.indicator_repo.get_indicators_by_type(indicator_type)

    def get_indicator_by_id(self, indicator_id: int) -> Dict:
        """Get specific indicator details"""
        indicator = self.indicator_repo.get_indicator_by_id(indicator_id)
        if not indicator:
            raise EntityNotFoundException("Technical Indicator", str(indicator_id))
        return indicator

    def get_indicator_by_name(self, name: str) -> Dict:
        """Get indicator by name"""
        indicator = self.indicator_repo.get_indicator_by_name(name)
        if not indicator:
            raise EntityNotFoundException("Technical Indicator", name)
        return indicator

    @validate_input()
    def calculate_indicator_values(self, params: Dict) -> Dict:
        """
        Calculate indicator values for given symbol and date range

        Args:
            params: {
                'indicator_name': str,
                'symbol': str,
                'start_date': str,
                'end_date': str,
                'custom_params': dict (optional)
            }
        """
        indicator_name = params['indicator_name']
        symbol = params['symbol']
        start_date = params['start_date']
        end_date = params['end_date']
        custom_params = params.get('custom_params', None)

        # Get indicator configuration from database
        indicator_config = self.get_indicator_by_name(indicator_name)

        # Convert full name to short code for calculation
        indicator_code = self._get_indicator_code(indicator_name)

        # Calculate using advanced indicators service
        result = self.advanced_indicators.calculate_indicator(
            symbol=symbol,
            indicator_name=indicator_code,
            start_date=start_date,
            end_date=end_date,
            custom_params=custom_params
        )

        return {
            **indicator_config,
            'values': result['data'],
            'parameters_used': result['parameters']
        }

    def get_solution_indicators(self, solution_id: int) -> Dict[str, Dict]:
        """
        Get all indicators configured for a solution
        Returns dict with keys for each indicator category
        """
        indicators = self.indicator_repo.get_solution_indicators(solution_id)

        # Organize by category - includes all indicator types
        result = {
            'trend': None,
            'momentum': None,
            'volatility': None,
            'volume': None,
            'support_resistance': None,
            'price_transform': None,
            'bill_williams': None
        }

        for ind in indicators:
            result[ind['indicator_category']] = {
                'id': ind['indicator_id'],
                'name': ind['indicator_name'],
                'description': ind['description'],
                'covariate_type': ind['covariate_type'],
                'parameters': ind['parameters']
            }

        return result

    def _validate_covariate_compatibility(self, solution_id: int, covariate_type: str) -> None:
        """
        Validate that the covariate_type is compatible with the solution's model

        Args:
            solution_id: Solution ID
            covariate_type: Requested covariate type ('past', 'future', 'both')

        Raises:
            ValidationException: If covariate type is incompatible with model
        """
        # Import here to avoid circular dependency
        from repositories.predict_solution_repository import PredictSolutionRepository
        from repositories.model_repository import ModelRepository
        from repositories.model_capability_repository import ModelCapabilityRepository

        solution_repo = PredictSolutionRepository()
        model_repo = ModelRepository()
        capability_repo = ModelCapabilityRepository()

        # Get solution
        solution = solution_repo.get_solution_by_id(solution_id)
        if not solution:
            raise ValidationException(f"Solution {solution_id} not found")

        # Get model instance to retrieve model_type
        model = model_repo.get_model_by_id(solution['model_id'])
        if not model:
            raise ValidationException(f"Model {solution['model_id']} not found")

        # Get model capabilities from the capabilities table (not model_instances)
        try:
            capabilities = capability_repo.get_capabilities_by_model_type(model['model_type'])
            supports_past = capabilities['supports_past_covariates']
            supports_future = capabilities['supports_future_covariates']
        except Exception:
            # Fallback to model_instances table if capabilities not found
            # (for backward compatibility during transition period)
            supports_past = bool(model.get('past_covariate', 0))
            supports_future = bool(model.get('future_covariate', 0))

        # Validate compatibility
        if covariate_type == 'past' and not supports_past:
            raise ValidationException(
                f"Model '{model['model_name']}' does not support past covariates. "
                f"Cannot set covariate_type='past'."
            )

        if covariate_type == 'future' and not supports_future:
            raise ValidationException(
                f"Model '{model['model_name']}' does not support future covariates. "
                f"Cannot set covariate_type='future'."
            )

        if covariate_type == 'both':
            if not supports_past:
                raise ValidationException(
                    f"Model '{model['model_name']}' does not support past covariates. "
                    f"Cannot set covariate_type='both'."
                )
            if not supports_future:
                raise ValidationException(
                    f"Model '{model['model_name']}' does not support future covariates. "
                    f"Cannot set covariate_type='both'."
                )

    @validate_input()
    def add_solution_indicator(self, params: Dict) -> int:
        """
        Add an indicator to a solution

        Args:
            params: {
                'solution_id': int,
                'indicator_id': int,
                'indicator_category': str (or 'indicator_type' for backward compatibility),
                'covariate_type': str (optional, default 'past'),
                'parameters': dict (optional)
            }

        Raises:
            ValidationException: If covariate_type is incompatible with model
        """
        solution_id = params['solution_id']
        indicator_id = params['indicator_id']
        # Support both old and new field names
        indicator_category = params.get('indicator_category') or params.get('indicator_type')
        covariate_type = params.get('covariate_type', 'past')
        parameters = params.get('parameters', None)

        if not indicator_category:
            raise ValidationException("indicator_category (or indicator_type) is required")

        # Validate covariate_type
        if covariate_type not in ['past', 'future', 'both']:
            raise ValidationException("covariate_type must be 'past', 'future', or 'both'")

        # Validate indicator exists
        indicator = self.get_indicator_by_id(indicator_id)

        # Validate category matches
        if indicator['type'] != indicator_category:
            raise ValidationException(
                f"Indicator category mismatch. Expected {indicator_category}, got {indicator['type']}"
            )

        # Validate covariate compatibility with model
        self._validate_covariate_compatibility(solution_id, covariate_type)

        # Add to database
        return self.indicator_repo.add_solution_indicator(
            solution_id, indicator_id, indicator_category, covariate_type, parameters
        )

    @validate_input()
    def update_solution_indicator(self, params: Dict) -> bool:
        """
        Update indicator parameters for a solution

        Args:
            params: {
                'solution_id': int,
                'indicator_id': int,
                'parameters': dict
            }
        """
        return self.indicator_repo.update_solution_indicator(
            params['solution_id'],
            params['indicator_id'],
            params['parameters']
        )

    @validate_input()
    def remove_solution_indicator(self, solution_id: int, indicator_id: int) -> bool:
        """Remove an indicator from a solution"""
        return self.indicator_repo.remove_solution_indicator(solution_id, indicator_id)

    @validate_input()
    def set_solution_indicators(self, params: Dict) -> Dict:
        """
        Set all four indicators for a solution at once

        Args:
            params: {
                'solution_id': int,
                'trend_indicator': {'id': int, 'covariate_type': str, 'parameters': dict},
                'momentum_indicator': {'id': int, 'covariate_type': str, 'parameters': dict},
                'volatility_indicator': {'id': int, 'covariate_type': str, 'parameters': dict},
                'volume_indicator': {'id': int, 'covariate_type': str, 'parameters': dict}
            }
        """
        solution_id = params['solution_id']

        # Clear existing indicators
        self.indicator_repo.clear_solution_indicators(solution_id)

        # Add new indicators
        results = {}
        indicator_categories = ['trend', 'momentum', 'volatility', 'volume']

        for ind_category in indicator_categories:
            key = f'{ind_category}_indicator'
            if key in params and params[key]:
                indicator_data = params[key]

                self.add_solution_indicator({
                    'solution_id': solution_id,
                    'indicator_id': indicator_data['id'],
                    'indicator_category': ind_category,
                    'covariate_type': indicator_data.get('covariate_type', 'past'),
                    'parameters': indicator_data.get('parameters', None)
                })

                results[ind_category] = indicator_data

        return results

    @validate_input()
    def calculate_solution_indicators(self, params: Dict) -> Dict:
        """
        Calculate all indicators for a solution and return as DataFrame-compatible structure

        Args:
            params: {
                'solution_id': int,
                'symbol': str,
                'start_date': str,
                'end_date': str
            }

        Returns:
            Dict with indicator values organized by type, ready for model input
        """
        solution_id = params['solution_id']
        symbol = params['symbol']
        start_date = params['start_date']
        end_date = params['end_date']

        # Get solution's configured indicators
        solution_indicators = self.get_solution_indicators(solution_id)

        # Calculate each indicator
        calculated_values = {}

        for ind_type, ind_config in solution_indicators.items():
            if ind_config is None:
                continue

            # Convert full indicator name to short code for calculation
            indicator_code = self._get_indicator_code(ind_config['name'])

            result = self.advanced_indicators.calculate_indicator(
                symbol=symbol,
                indicator_name=indicator_code,
                start_date=start_date,
                end_date=end_date,
                custom_params=ind_config['parameters']
            )

            calculated_values[ind_type] = {
                'name': ind_config['name'],
                'data': result['data']
            }

        return calculated_values

    def build_indicator_dataframe(self, calculated_indicators: Dict) -> pd.DataFrame:
        """
        Build a pandas DataFrame from calculated indicators for model training/prediction

        Args:
            calculated_indicators: Output from calculate_solution_indicators()

        Returns:
            DataFrame with columns: date, trend, momentum, volatility, volume

        Raises:
            ValueError: If insufficient valid data after indicator calculations
        """
        print("\n========== DEBUG: build_indicator_dataframe ==========")
        print(f"Calculated indicators keys: {list(calculated_indicators.keys())}")

        dataframes = []

        for ind_type, ind_data in calculated_indicators.items():
            if ind_data is None:
                print(f"[{ind_type}] is None, skipping")
                continue

            print(f"\n[{ind_type}] Processing indicator: {ind_data['name']}")
            print(f"[{ind_type}] Raw data sample (first 3 items): {ind_data['data'][:3] if len(ind_data['data']) > 0 else 'EMPTY'}")
            print(f"[{ind_type}] Total data points: {len(ind_data['data'])}")

            # Convert indicator data to DataFrame
            df = pd.DataFrame(ind_data['data'])

            if df.empty:
                raise ValueError(
                    f"No data returned for {ind_type} indicator ({ind_data['name']}). "
                    f"This may indicate insufficient price data for the selected date range."
                )

            print(f"[{ind_type}] DataFrame shape before processing: {df.shape}")
            print(f"[{ind_type}] DataFrame columns: {list(df.columns)}")
            print(f"[{ind_type}] First 3 rows:\n{df.head(3)}")

            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')

            # Extract primary value from indicator
            # (most indicators have a primary value, some have multiple)
            primary_col = self._get_primary_indicator_column(ind_data['name'], df.columns)
            print(f"[{ind_type}] Primary column selected: {primary_col}")

            if primary_col:
                df_renamed = df[[primary_col]].rename(columns={primary_col: ind_type})

                # Convert Python None to pandas NaN for proper handling
                df_renamed[ind_type] = df_renamed[ind_type].replace({None: np.nan})

                print(f"[{ind_type}] Non-null count in primary column: {df_renamed[ind_type].notna().sum()}")
                print(f"[{ind_type}] Null count in primary column: {df_renamed[ind_type].isna().sum()}")
                print(f"[{ind_type}] Sample values: {df_renamed[ind_type].head(10).tolist()}")

                # Check if indicator has any valid values
                if df_renamed[ind_type].notna().sum() == 0:
                    print(f"[{ind_type}] WARNING: All values are None/NaN, skipping this indicator")

                    # Build user-friendly suggestions
                    suggestions = [
                        {
                            'title': 'Extend Date Range (Recommended)',
                            'description': 'Increase your training date range to at least 6-12 months. This gives all indicators enough historical data to calculate properly and improves model training quality.',
                            'action': 'Extend the start date in the Training tab to at least 6 months before the end date.'
                        },
                        {
                            'title': f'Reduce {ind_data["name"]} Period',
                            'description': f'Change the period parameter for {ind_data["name"]} from its current value to a smaller number (e.g., 10 or 5). This requires fewer data points to start calculating.',
                            'action': f'Edit the {ind_type} indicator parameters in the General Information tab and reduce the period value.'
                        },
                        {
                            'title': f'Choose Different {ind_type.title()} Indicator',
                            'description': f'Replace {ind_data["name"]} with a different {ind_type} indicator that has a shorter warm-up period, such as ATR (14 days) or a custom indicator.',
                            'action': f'Change the {ind_type} indicator selection in the General Information tab.'
                        }
                    ]

                    raise IndicatorValidationException(
                        indicator_name=ind_data['name'],
                        indicator_type=ind_type,
                        message=f"Indicator '{ind_data['name']}' ({ind_type}) returned all None/NaN values. "
                                f"This typically happens when the date range is too short for the indicator's period. "
                                f"The indicator requires a warm-up period before it can calculate valid values.",
                        suggestions=suggestions
                    )

                dataframes.append(df_renamed)

        print(f"\nTotal dataframes to merge: {len(dataframes)}")

        # Merge all indicator dataframes
        if not dataframes:
            print("No dataframes to merge, returning empty DataFrame")
            return pd.DataFrame()

        result_df = dataframes[0]
        print(f"Starting with dataframe shape: {result_df.shape}")

        for i, df in enumerate(dataframes[1:], 1):
            print(f"Merging dataframe {i}, shape: {df.shape}")
            result_df = result_df.join(df, how='outer')
            print(f"After merge {i}, shape: {result_df.shape}")

        print(f"\nAfter all merges - shape: {result_df.shape}")
        print(f"Columns: {list(result_df.columns)}")
        print(f"Total rows: {len(result_df)}")
        print(f"Null counts per column:\n{result_df.isna().sum()}")
        print(f"First 10 rows:\n{result_df.head(10)}")

        # Fill NaN values using both forward and backward fill
        # This handles initial NaN values from indicator warm-up periods
        print("\nApplying forward fill and backward fill...")
        result_df = result_df.ffill().bfill()
        print(f"After ffill/bfill - null counts:\n{result_df.isna().sum()}")
        print(f"First 10 rows after fill:\n{result_df.head(10)}")

        # Drop any remaining rows with NaN values
        print(f"\nBefore dropna - shape: {result_df.shape}")
        result_df = result_df.dropna()
        print(f"After dropna - shape: {result_df.shape}")

        if len(result_df) > 0:
            print(f"First 5 rows after dropna:\n{result_df.head()}")
            print(f"Last 5 rows after dropna:\n{result_df.tail()}")

        # Validate we have sufficient data after processing
        if result_df.empty or len(result_df) < 2:
            print(f"\n!!! INSUFFICIENT DATA !!!")
            print(f"Final row count: {len(result_df)}")
            raise ValueError(
                f"Insufficient valid indicator data after processing. "
                f"Only {len(result_df)} valid data points found. "
                f"Technical indicators require a minimum date range to calculate values. "
                f"Please try:\n"
                f"1. Extending the date range (recommend at least 60-90 days)\n"
                f"2. Ensuring the stock has trading data for the selected period\n"
                f"3. Checking that the selected indicators have compatible parameters"
            )

        print(f"\n========== SUCCESS: Returning {len(result_df)} valid data points ==========\n")
        return result_df.reset_index()

    def _get_primary_indicator_column(self, indicator_name: str, columns: List[str]) -> Optional[str]:
        """Get the primary value column for an indicator"""
        # Mapping of indicator names to their primary column
        primary_columns = {
            # Trend - Moving Averages
            'SMA': 'sma', 'EMA': 'ema', 'WMA': 'wma',
            'DEMA': 'dema', 'TEMA': 'tema',

            # Trend - Direction
            'MACD': 'macd', 'ADX': 'adx', 'PSAR': 'psar',
            'SUPERTREND': 'supertrend',
            'ICHIMOKU': 'tenkan',  # Use tenkan-sen as primary
            'AROON': 'aroon_indicator',
            'VORTEX': 'vi_diff',

            # Momentum
            'RSI': 'rsi', 'STOCH': 'stoch_k', 'STOCH_RSI': 'stoch_rsi_k',
            'CCI': 'cci', 'MOM': 'momentum', 'ROC': 'roc',
            'WILLIAMS_R': 'williams_r',
            'TSI': 'tsi', 'UO': 'uo', 'AO': 'ao',

            # Volatility
            'BB': 'bb_middle', 'ATR': 'atr',
            'KELTNER': 'kc_middle', 'DONCHIAN': 'dc_middle',
            'STDDEV': 'std_dev', 'HV': 'hv',

            # Volume
            'VOLUME': 'volume', 'OBV': 'obv', 'VWAP': 'vwap',
            'MFI': 'mfi', 'AD': 'ad', 'CMF': 'cmf',
            'CHO': 'cho', 'VOSC': 'vosc', 'EOM': 'eom',
            'FI': 'fi', 'NVI': 'nvi', 'PVI': 'pvi',
            'Volume_MA': 'volume_sma',

            # Support & Resistance
            'PIVOT': 'pivot',
            'FIB_RET': 'level_500',  # 50% retracement as primary
            'FIB_EXT': 'ext_1618',  # 161.8% extension as primary

            # Price Transform
            'HEIKIN_ASHI': 'ha_close',
            'RENKO': 'renko_direction',
            'TP': 'typical_price',
            'MP': 'median_price',
            'WC': 'weighted_close',

            # Bill Williams
            'ALLIGATOR': 'jaw',  # Jaw line as primary
            'FRACTALS': 'fractal_up',
            'GATOR': 'gator_upper',
            'MFI_BW': 'mfi_bw',
            'AC': 'ac',
        }

        primary = primary_columns.get(indicator_name)
        if primary and primary in columns:
            return primary

        # Fallback to first non-date column
        for col in columns:
            if col != 'date':
                return col

        return None

    def validate_solution_indicators(self, solution_id: int) -> Dict:
        """
        Validate that a solution has all required indicators configured

        Returns:
            {
                'is_valid': bool,
                'missing_types': list,
                'configured_types': list
            }
        """
        indicators = self.get_solution_indicators(solution_id)

        missing_types = []
        configured_types = []

        for ind_type, ind_config in indicators.items():
            if ind_config is None:
                missing_types.append(ind_type)
            else:
                configured_types.append(ind_type)

        return {
            'is_valid': len(missing_types) == 0,
            'missing_types': missing_types,
            'configured_types': configured_types
        }

    @validate_input()
    def create_indicator(self, params: Dict) -> Dict:
        """
        Create a new technical indicator

        Args:
            params: {
                'name': str,
                'type': str (trend, momentum, volatility, volume),
                'description': str,
                'calculation_function': str,
                'default_parameters': dict
            }
        """
        # Validate type
        valid_types = ['trend', 'momentum', 'volatility', 'volume', 'support_resistance', 'price_transform', 'bill_williams']
        if params['type'] not in valid_types:
            raise ValidationException(f"Invalid indicator type. Must be one of: {', '.join(valid_types)}")

        # Create indicator
        indicator_id = self.indicator_repo.create_indicator(
            name=params['name'],
            indicator_type=params['type'],
            description=params['description'],
            calculation_function=params['calculation_function'],
            default_parameters=params['default_parameters']
        )

        return self.get_indicator_by_id(indicator_id)

    @validate_input()
    def update_indicator(self, indicator_id: int, params: Dict) -> Dict:
        """
        Update an existing technical indicator

        Args:
            indicator_id: int
            params: {
                'name': str,
                'type': str,
                'description': str,
                'calculation_function': str,
                'default_parameters': dict
            }
        """
        # Validate indicator exists
        indicator = self.get_indicator_by_id(indicator_id)

        # Validate type if provided
        if 'type' in params:
            valid_types = ['trend', 'momentum', 'volatility', 'volume', 'support_resistance', 'price_transform', 'bill_williams']
            if params['type'] not in valid_types:
                raise ValidationException(f"Invalid indicator type. Must be one of: {', '.join(valid_types)}")

        # Update indicator
        success = self.indicator_repo.update_indicator(
            indicator_id=indicator_id,
            name=params.get('name'),
            indicator_type=params.get('type'),
            description=params.get('description'),
            calculation_function=params.get('calculation_function'),
            default_parameters=params.get('default_parameters')
        )

        if not success:
            raise EntityNotFoundException("Technical Indicator", str(indicator_id))

        return self.get_indicator_by_id(indicator_id)

    def delete_indicator(self, indicator_id: int) -> bool:
        """Delete a technical indicator"""
        # Validate indicator exists
        indicator = self.get_indicator_by_id(indicator_id)

        # Delete indicator
        return self.indicator_repo.delete_indicator(indicator_id)
