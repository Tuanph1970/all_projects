"""
Trading Simulator - Orchestrates ML predictions and trading decisions
"""

from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
from services.prediction_strategies import PredictionStrategy
from services.portfolio_manager import Portfolio, TransactionType
from core.decorators import validate_input
from core.exceptions import SimulationException


class TradingStrategy:
    """
    Trading decision logic based on predictions
    """

    def __init__(self, threshold_buy: float = 0.02, threshold_sell: float = -0.01,
                 position_size: float = 0.3):
        """
        Args:
            threshold_buy: Buy if predicted return > threshold (e.g., 0.02 = 2%)
            threshold_sell: Sell if predicted return < threshold (e.g., -0.01 = -1%)
            position_size: Fraction of available cash to use per trade (0.3 = 30%)
        """
        self.threshold_buy = threshold_buy
        self.threshold_sell = threshold_sell
        self.position_size = position_size

    def decide(self, current_price: float, predicted_price: float,
               portfolio: Portfolio) -> Tuple[TransactionType, int]:
        """
        Decide trading action based on prediction

        Args:
            current_price: Current stock price
            predicted_price: Predicted future price
            portfolio: Current portfolio state

        Returns:
            (action, shares) tuple
        """
        # Calculate predicted return
        predicted_return = (predicted_price - current_price) / current_price

        # Buy signal
        if predicted_return > self.threshold_buy:
            # Calculate shares to buy based on position size
            available_cash = portfolio.cash * self.position_size
            shares_to_buy = int(available_cash // current_price)

            if shares_to_buy > 0:
                return TransactionType.BUY, shares_to_buy

        # Sell signal
        elif predicted_return < self.threshold_sell and portfolio.shares_owned > 0:
            # Sell all shares on sell signal
            return TransactionType.SELL, portfolio.shares_owned

        # Hold
        return TransactionType.HOLD, 0


class TradingSimulator:
    """
    Main simulator that orchestrates prediction and trading
    """

    def __init__(self, prediction_strategy: PredictionStrategy,
                 trading_strategy: TradingStrategy,
                 portfolio: Portfolio):
        self.prediction_strategy = prediction_strategy
        self.trading_strategy = trading_strategy
        self.portfolio = portfolio

        self.predictions: List[float] = []
        self.actual_prices: List[float] = []
        self.dates: List[datetime] = []

    def run_simulation(self, prices_df: pd.DataFrame, indicators_df: pd.DataFrame = None,
                      train_split: float = 0.8) -> Dict:
        """
        Run complete trading simulation

        Args:
            prices_df: DataFrame with columns ['date', 'close']
            indicators_df: Optional DataFrame with technical indicators
            train_split: Fraction of data to use for training (0.8 = 80%)

        Returns:
            Simulation results dictionary
        """
        # Prepare data
        prices = prices_df['close']
        dates = pd.to_datetime(prices_df['date'])

        # Prepare sequences for prediction
        X, y = self.prediction_strategy.prepare_data(prices, indicators_df)

        # Split into train and test
        split_idx = int(len(X) * train_split)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Train model
        train_metrics = self.prediction_strategy.train(X_train, y_train, X_test, y_test)

        # Make predictions on test set
        predictions_scaled = self.prediction_strategy.predict(X_test)

        # Inverse transform predictions to original scale
        predictions = self._inverse_transform_predictions(predictions_scaled, X_test)

        # Get actual prices for test period
        test_start_idx = self.prediction_strategy.lookback_period + split_idx
        test_prices = prices.iloc[test_start_idx:].values
        test_dates = dates.iloc[test_start_idx:].values

        # Run trading simulation on test period
        for i, (date, current_price, predicted_price) in enumerate(zip(test_dates, test_prices, predictions)):
            self.dates.append(date)
            self.actual_prices.append(current_price)
            self.predictions.append(predicted_price)

            # Decide action
            action, shares = self.trading_strategy.decide(
                current_price, predicted_price, self.portfolio
            )

            # Execute action
            if action == TransactionType.BUY:
                self.portfolio.buy(date, current_price, shares)
            elif action == TransactionType.SELL:
                self.portfolio.sell(date, current_price, shares)
            else:
                self.portfolio.hold(date, current_price)

        # Calculate final metrics
        test_prices_series = pd.Series(test_prices, index=test_dates)
        portfolio_metrics = self.portfolio.calculate_metrics(test_prices_series)

        # Prepare results
        results = {
            'model_name': self.prediction_strategy.get_model_name(),
            'training_metrics': train_metrics,
            'portfolio_metrics': portfolio_metrics.to_dict(),
            'transaction_history': self.portfolio.get_transaction_history(),
            'time_series': self._prepare_time_series_data(),
            'buy_sell_points': self.portfolio.get_buy_sell_points(),
            'prediction_accuracy': self._calculate_prediction_accuracy()
        }

        return results

    def _inverse_transform_predictions(self, predictions_scaled: np.ndarray,
                                      X_test: np.ndarray) -> np.ndarray:
        """
        Inverse transform scaled predictions to original price scale

        Args:
            predictions_scaled: Scaled predictions
            X_test: Test sequences (needed for scaler context)

        Returns:
            Predictions in original scale
        """
        # Create dummy array with same shape as scaler expects
        dummy = np.zeros((len(predictions_scaled), X_test.shape[2]))
        dummy[:, 0] = predictions_scaled

        # Inverse transform
        predictions_original = self.prediction_strategy.scaler.inverse_transform(dummy)[:, 0]

        return predictions_original

    def _prepare_time_series_data(self) -> List[Dict]:
        """Prepare time series data for visualization"""
        time_series = []

        for i, (date, actual, predicted) in enumerate(zip(self.dates, self.actual_prices, self.predictions)):
            time_series.append({
                'date': date.isoformat() if isinstance(date, datetime) else str(date),
                'actual_price': float(actual),
                'predicted_price': float(predicted),
                'portfolio_value': float(self.portfolio.portfolio_values[i]) if i < len(self.portfolio.portfolio_values) else 0
            })

        return time_series

    def _calculate_prediction_accuracy(self) -> Dict:
        """Calculate prediction accuracy metrics"""
        actual = np.array(self.actual_prices)
        predicted = np.array(self.predictions)

        # Calculate metrics
        mae = np.mean(np.abs(actual - predicted))
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        mape = np.mean(np.abs((actual - predicted) / actual)) * 100

        # Direction accuracy (did we predict up/down correctly?)
        if len(actual) > 1:
            actual_direction = np.diff(actual) > 0
            predicted_direction = np.diff(predicted) > 0
            direction_accuracy = np.mean(actual_direction == predicted_direction) * 100
        else:
            direction_accuracy = 0

        return {
            'mae': float(mae),
            'rmse': float(rmse),
            'mape': float(mape),
            'direction_accuracy': float(direction_accuracy)
        }


class SimulationBuilder:
    """
    Builder pattern for creating simulation configurations
    """

    def __init__(self):
        self._model_type = None
        self._model_params = {}
        self._trading_params = {}
        self._portfolio_params = {}

    def with_model(self, model_type: str, **model_params) -> 'SimulationBuilder':
        """Set ML model configuration"""
        self._model_type = model_type
        self._model_params = model_params
        return self

    def with_trading_strategy(self, threshold_buy: float = 0.02,
                              threshold_sell: float = -0.01,
                              position_size: float = 0.3) -> 'SimulationBuilder':
        """Set trading strategy parameters"""
        self._trading_params = {
            'threshold_buy': threshold_buy,
            'threshold_sell': threshold_sell,
            'position_size': position_size
        }
        return self

    def with_portfolio(self, initial_capital: float,
                      commission_rate: float = 0.001) -> 'SimulationBuilder':
        """Set portfolio parameters"""
        self._portfolio_params = {
            'initial_capital': initial_capital,
            'commission_rate': commission_rate
        }
        return self

    def build(self) -> TradingSimulator:
        """Build the trading simulator"""
        from services.prediction_strategies import PredictionStrategyFactory

        # Create prediction strategy
        if not self._model_type:
            raise SimulationException("Simulation", "Model type not specified")

        prediction_strategy = PredictionStrategyFactory.create_strategy(
            self._model_type, **self._model_params
        )

        # Create trading strategy
        trading_strategy = TradingStrategy(**self._trading_params)

        # Create portfolio
        portfolio = Portfolio(**self._portfolio_params)

        # Create simulator
        return TradingSimulator(prediction_strategy, trading_strategy, portfolio)
