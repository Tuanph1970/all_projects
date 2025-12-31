"""
Stock Trading Simulation Service
Main orchestrator for ML-based trading simulations
"""

from typing import Dict, List
import pandas as pd
from services.stock_market_service import CompanyService
from services.indicator_service import IndicatorService
from services.trading_simulator import SimulationBuilder
from services.prediction_strategies import PredictionStrategyFactory
from services.pretrained_prediction_strategy import PretrainedPredictionStrategy
from repositories.predict_solution_repository import PredictSolutionRepository
from core.decorators import validate_input
from core.exceptions import SimulationException, ValidationException


class SimulationService:
    """
    Main service for running stock trading simulations with ML predictions
    """

    def __init__(self):
        self.company_service = CompanyService()
        self.indicator_service = IndicatorService()
        self.solution_repo = PredictSolutionRepository()

    @validate_input()
    def run_simulation(self, params: Dict) -> Dict:
        """
        Run a complete trading simulation

        Args:
            params: {
                'ticker': str,
                'start_date': str (YYYY-MM-DD),
                'end_date': str (YYYY-MM-DD),
                'model_type': str ('RNN', 'XGBoost', 'RandomForest'),
                'initial_capital': float,
                'model_params': dict (optional),
                'trading_params': dict (optional),
                'use_indicators': bool (optional, default False),
                'indicator_names': list (optional)
            }

        Returns:
            Simulation results with predictions, trades, and metrics
        """
        try:
            # Extract parameters
            ticker = params['ticker']
            start_date = params['start_date']
            end_date = params['end_date']
            initial_capital = float(params['initial_capital'])
            use_pretrained = params.get('use_pretrained_model', False)

            # Get stock price data
            price_df = self._get_price_data(ticker, start_date, end_date)

            if len(price_df) < 100:
                raise ValidationException(
                    f"Insufficient data. Got {len(price_df)} rows, need at least 100 for simulation."
                )

            # Extract trading parameters
            trading_params = params.get('trading_params', {})

            # Check if using pre-trained model or training new one
            if use_pretrained:
                # Use pre-trained model from solution
                solution_id = params.get('pretrained_solution_id')
                if not solution_id:
                    raise ValidationException("pretrained_solution_id is required when use_pretrained_model is True")

                # Create pretrained prediction strategy
                prediction_strategy = PretrainedPredictionStrategy(solution_id)
                model_type = prediction_strategy.get_model_name()

                # Build simulator with pretrained model
                from services.trading_simulator import TradingSimulator, TradingStrategy
                from services.portfolio_manager import Portfolio

                trading_strategy = TradingStrategy(
                    threshold_buy=trading_params.get('threshold_buy', 0.02),
                    threshold_sell=trading_params.get('threshold_sell', -0.01),
                    position_size=trading_params.get('position_size', 0.3)
                )

                portfolio = Portfolio(
                    initial_capital=initial_capital,
                    commission_rate=trading_params.get('commission_rate', 0.001)
                )

                simulator = TradingSimulator(prediction_strategy, trading_strategy, portfolio)

                # Run simulation with pretrained model
                results = simulator.run_simulation(prices_df=price_df, train_split=0)  # No training needed

                # Add solution info to metadata
                results['metadata'] = {
                    'ticker': ticker,
                    'start_date': start_date,
                    'end_date': end_date,
                    'model_type': 'Pretrained',
                    'solution_info': prediction_strategy.get_solution_info(),
                    'initial_capital': initial_capital,
                    'used_pretrained': True,
                    'data_points': len(price_df)
                }

            else:
                # Train new model
                model_type = params['model_type']

                # Validate model type
                available_models = PredictionStrategyFactory.get_available_models()
                if model_type not in available_models:
                    raise ValidationException(
                        f"Invalid model type '{model_type}'. Available: {', '.join(available_models)}"
                    )

                # Get technical indicators if requested
                indicators_df = None
                if params.get('use_indicators', False):
                    indicators_df = self._get_indicators_data(
                        ticker, start_date, end_date, params.get('indicator_names', [])
                    )

                # Extract model parameters
                model_params = params.get('model_params', {})

                # Build simulator
                simulator = (SimulationBuilder()
                            .with_model(model_type, **model_params)
                            .with_trading_strategy(
                                threshold_buy=trading_params.get('threshold_buy', 0.02),
                                threshold_sell=trading_params.get('threshold_sell', -0.01),
                                position_size=trading_params.get('position_size', 0.3)
                            )
                            .with_portfolio(
                                initial_capital=initial_capital,
                                commission_rate=trading_params.get('commission_rate', 0.001)
                            )
                            .build())

                # Run simulation with new training
                results = simulator.run_simulation(
                    prices_df=price_df,
                    indicators_df=indicators_df,
                    train_split=params.get('train_split', 0.8)
                )

                # Add metadata
                results['metadata'] = {
                    'ticker': ticker,
                    'start_date': start_date,
                    'end_date': end_date,
                    'model_type': model_type,
                    'initial_capital': initial_capital,
                    'used_indicators': params.get('use_indicators', False),
                    'used_pretrained': False,
                    'data_points': len(price_df)
                }

            return results

        except Exception as e:
            raise SimulationException(model_type if 'model_type' in params else 'Unknown', str(e))

    def _get_price_data(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get historical price data"""
        df = self.company_service.get_price_history_df(ticker, "VCI")
        df = df[['time', 'close']].copy()
        df.columns = ['date', 'close']
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')

        # Filter by date range
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)

        return df

    def _get_indicators_data(self, ticker: str, start_date: str, end_date: str,
                            indicator_names: List[str]) -> pd.DataFrame:
        """Get technical indicators data"""
        if not indicator_names:
            # Default indicators
            indicator_names = ['SMA', 'RSI', 'MACD', 'BB']

        all_indicators = []

        for indicator_name in indicator_names:
            try:
                result = self.indicator_service.calculate_indicator_values({
                    'indicator_name': indicator_name,
                    'symbol': ticker,
                    'start_date': start_date,
                    'end_date': end_date
                })

                if result and 'values' in result:
                    indicator_df = pd.DataFrame(result['values'])
                    indicator_df['date'] = pd.to_datetime(indicator_df['date'])
                    all_indicators.append(indicator_df.set_index('date'))

            except Exception as e:
                # Skip indicators that fail to calculate
                print(f"Warning: Could not calculate {indicator_name}: {str(e)}")
                continue

        if all_indicators:
            # Merge all indicators
            indicators_df = pd.concat(all_indicators, axis=1)
            indicators_df = indicators_df.reset_index()
            return indicators_df
        else:
            return None

    def get_available_models(self) -> List[Dict]:
        """
        Get list of available prediction models

        Returns:
            List of model info dictionaries
        """
        models = PredictionStrategyFactory.get_available_models()

        model_info = []
        for model_type in models:
            info = {
                'model_type': model_type,
                'description': self._get_model_description(model_type),
                'default_params': self._get_default_model_params(model_type)
            }
            model_info.append(info)

        return model_info

    def _get_model_description(self, model_type: str) -> str:
        """Get model description"""
        descriptions = {
            'RNN': 'Recurrent Neural Network (LSTM) - Good for sequential time series data',
            'XGBoost': 'Gradient Boosting - Fast and accurate for structured data',
            'RandomForest': 'Random Forest - Robust ensemble method with feature importance'
        }
        return descriptions.get(model_type, 'No description available')

    def _get_default_model_params(self, model_type: str) -> Dict:
        """Get default model parameters"""
        defaults = {
            'RNN': {
                'lookback_period': 60,
                'lstm_units': [50, 50]
            },
            'XGBoost': {
                'lookback_period': 60,
                'n_estimators': 100,
                'max_depth': 7,
                'learning_rate': 0.1
            },
            'RandomForest': {
                'lookback_period': 60,
                'n_estimators': 100,
                'max_depth': 10,
                'min_samples_split': 5
            }
        }
        return defaults.get(model_type, {})

    def get_trained_solutions(self, user_id: str = None) -> List[Dict]:
        """
        Get list of user's trained solutions

        Args:
            user_id: Optional user filter

        Returns:
            List of trained solutions
        """
        solutions = self.solution_repo.get_trained_solutions(user_id)

        # Format for frontend
        return [{
            'solution_id': sol['id'],
            'solution_name': sol['solution_name'],
            'ticker': sol['ticker'],
            'model_name': sol['model_name'],
            'model_type': sol['model_type'],
            'training_period': f"{sol['start_training_date']} to {sol['end_training_date']}"
        } for sol in solutions]

    def get_simulation_config_template(self) -> Dict:
        """
        Get a template configuration for simulations

        Returns:
            Template configuration dictionary
        """
        return {
            'ticker': 'VNM',
            'start_date': '2023-01-01',
            'end_date': '2024-01-01',
            'model_type': 'XGBoost',
            'use_pretrained_model': False,  # NEW: Toggle between new training and pretrained
            'pretrained_solution_id': None,  # NEW: ID of pretrained solution to use
            'initial_capital': 100000000,  # 100M VND
            'model_params': {
                'lookback_period': 60,
                'n_estimators': 100,
                'max_depth': 7
            },
            'trading_params': {
                'threshold_buy': 0.02,  # Buy if predicted return > 2%
                'threshold_sell': -0.01,  # Sell if predicted return < -1%
                'position_size': 0.3,  # Use 30% of cash per trade
                'commission_rate': 0.001  # 0.1% commission
            },
            'use_indicators': False,
            'indicator_names': ['SMA', 'RSI', 'MACD'],
            'train_split': 0.8
        }
