"""
ML Prediction Strategies for Stock Trading Simulation
Implements Strategy Pattern for different ML models (RNN, XGBoost, Random Forest)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import xgboost as xgb
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from core.decorators import validate_input
from core.exceptions import PredictionException


class PredictionStrategy(ABC):
    """Abstract base class for prediction strategies"""

    def __init__(self, lookback_period: int = 60):
        self.lookback_period = lookback_period
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model = None
        self.is_trained = False

    @abstractmethod
    def build_model(self, input_shape: Tuple) -> None:
        """Build the ML model"""
        pass

    @abstractmethod
    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_val: np.ndarray = None, y_val: np.ndarray = None) -> Dict:
        """Train the model"""
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions"""
        pass

    def prepare_data(self, prices: pd.Series, indicators: pd.DataFrame = None) -> Tuple:
        """
        Prepare data for training/prediction

        Args:
            prices: Series of stock prices
            indicators: DataFrame with technical indicators (optional)

        Returns:
            X, y arrays ready for model training
        """
        # Combine prices with indicators if available
        if indicators is not None and not indicators.empty:
            features = pd.concat([prices, indicators], axis=1)
        else:
            features = prices.to_frame()

        # Scale features
        scaled_data = self.scaler.fit_transform(features)

        # Create sequences
        X, y = [], []
        for i in range(self.lookback_period, len(scaled_data)):
            X.append(scaled_data[i-self.lookback_period:i])
            y.append(scaled_data[i, 0])  # Predict close price

        return np.array(X), np.array(y)

    def get_model_name(self) -> str:
        """Return model name"""
        return self.__class__.__name__.replace('Strategy', '')


class LSTMModel(nn.Module):
    """PyTorch LSTM Model"""

    def __init__(self, input_size: int, lstm_units: List[int]):
        super(LSTMModel, self).__init__()
        self.lstm1 = nn.LSTM(input_size, lstm_units[0], batch_first=True)
        self.dropout1 = nn.Dropout(0.2)
        self.lstm2 = nn.LSTM(lstm_units[0], lstm_units[1], batch_first=True)
        self.dropout2 = nn.Dropout(0.2)
        self.fc1 = nn.Linear(lstm_units[1], 25)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(25, 1)

    def forward(self, x):
        lstm_out, _ = self.lstm1(x)
        lstm_out = self.dropout1(lstm_out)
        lstm_out, _ = self.lstm2(lstm_out)
        lstm_out = self.dropout2(lstm_out)
        # Take the last time step
        out = self.fc1(lstm_out[:, -1, :])
        out = self.relu(out)
        out = self.fc2(out)
        return out


class RNNPredictionStrategy(PredictionStrategy):
    """RNN/LSTM based prediction strategy using PyTorch"""

    def __init__(self, lookback_period: int = 60, lstm_units: List[int] = None):
        super().__init__(lookback_period)
        self.lstm_units = lstm_units or [50, 50]
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.criterion = nn.MSELoss()
        self.optimizer = None

    def build_model(self, input_shape: Tuple) -> None:
        """Build LSTM model"""
        input_size = input_shape[1]  # number of features
        self.model = LSTMModel(input_size, self.lstm_units).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)

    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_val: np.ndarray = None, y_val: np.ndarray = None) -> Dict:
        """Train LSTM model"""
        if self.model is None:
            self.build_model((X_train.shape[1], X_train.shape[2]))

        # Convert to PyTorch tensors
        X_train_tensor = torch.FloatTensor(X_train).to(self.device)
        y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1).to(self.device)

        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

        # Prepare validation data if available
        val_loader = None
        if X_val is not None:
            X_val_tensor = torch.FloatTensor(X_val).to(self.device)
            y_val_tensor = torch.FloatTensor(y_val).unsqueeze(1).to(self.device)
            val_dataset = TensorDataset(X_val_tensor, y_val_tensor)
            val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

        # Training loop
        epochs = 50
        patience = 10
        best_val_loss = float('inf')
        patience_counter = 0
        history = {'loss': [], 'mae': []}

        for epoch in range(epochs):
            # Training
            self.model.train()
            train_losses = []
            train_maes = []

            for batch_X, batch_y in train_loader:
                self.optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = self.criterion(outputs, batch_y)
                loss.backward()
                self.optimizer.step()

                train_losses.append(loss.item())
                mae = torch.mean(torch.abs(outputs - batch_y)).item()
                train_maes.append(mae)

            epoch_loss = np.mean(train_losses)
            epoch_mae = np.mean(train_maes)
            history['loss'].append(epoch_loss)
            history['mae'].append(epoch_mae)

            # Validation
            if val_loader is not None:
                self.model.eval()
                val_losses = []
                with torch.no_grad():
                    for batch_X, batch_y in val_loader:
                        outputs = self.model(batch_X)
                        val_loss = self.criterion(outputs, batch_y)
                        val_losses.append(val_loss.item())

                val_loss = np.mean(val_losses)

                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    # Save best model state
                    best_model_state = self.model.state_dict().copy()
                else:
                    patience_counter += 1
                    if patience_counter >= patience:
                        # Restore best weights
                        self.model.load_state_dict(best_model_state)
                        break

        self.is_trained = True

        return {
            'final_loss': float(history['loss'][-1]),
            'final_mae': float(history['mae'][-1]),
            'epochs_trained': len(history['loss'])
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using LSTM"""
        if not self.is_trained:
            raise PredictionException("RNN", "Model not trained")

        self.model.eval()
        X_tensor = torch.FloatTensor(X).to(self.device)

        with torch.no_grad():
            predictions = self.model(X_tensor)

        return predictions.cpu().numpy().flatten()


class XGBoostPredictionStrategy(PredictionStrategy):
    """XGBoost based prediction strategy"""

    def __init__(self, lookback_period: int = 60, n_estimators: int = 100,
                 max_depth: int = 7, learning_rate: float = 0.1):
        super().__init__(lookback_period)
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate

    def build_model(self, input_shape: Tuple) -> None:
        """Build XGBoost model"""
        self.model = xgb.XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            objective='reg:squarederror',
            booster='gbtree',
            random_state=42
        )

    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_val: np.ndarray = None, y_val: np.ndarray = None) -> Dict:
        """Train XGBoost model"""
        # XGBoost needs 2D input, so flatten sequences
        X_train_flat = X_train.reshape(X_train.shape[0], -1)

        if self.model is None:
            self.build_model(X_train_flat.shape)

        eval_set = [(X_val.reshape(X_val.shape[0], -1), y_val)] if X_val is not None else None

        self.model.fit(
            X_train_flat, y_train,
            eval_set=eval_set,
            verbose=False
        )

        self.is_trained = True

        # Calculate training metrics
        train_pred = self.model.predict(X_train_flat)
        train_mse = np.mean((train_pred - y_train) ** 2)
        train_mae = np.mean(np.abs(train_pred - y_train))

        return {
            'final_loss': float(train_mse),
            'final_mae': float(train_mae),
            'feature_importance': self.model.feature_importances_.tolist()
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using XGBoost"""
        if not self.is_trained:
            raise PredictionException("XGBoost", "Model not trained")

        X_flat = X.reshape(X.shape[0], -1)
        predictions = self.model.predict(X_flat)
        return predictions


class RandomForestPredictionStrategy(PredictionStrategy):
    """Random Forest based prediction strategy"""

    def __init__(self, lookback_period: int = 60, n_estimators: int = 100,
                 max_depth: int = 10, min_samples_split: int = 5):
        super().__init__(lookback_period)
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split

    def build_model(self, input_shape: Tuple) -> None:
        """Build Random Forest model"""
        self.model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            random_state=42,
            n_jobs=-1
        )

    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_val: np.ndarray = None, y_val: np.ndarray = None) -> Dict:
        """Train Random Forest model"""
        # Random Forest needs 2D input, so flatten sequences
        X_train_flat = X_train.reshape(X_train.shape[0], -1)

        if self.model is None:
            self.build_model(X_train_flat.shape)

        self.model.fit(X_train_flat, y_train)

        self.is_trained = True

        # Calculate training metrics
        train_pred = self.model.predict(X_train_flat)
        train_mse = np.mean((train_pred - y_train) ** 2)
        train_mae = np.mean(np.abs(train_pred - y_train))

        results = {
            'final_loss': float(train_mse),
            'final_mae': float(train_mae),
            'feature_importance': self.model.feature_importances_.tolist()
        }

        # Add validation metrics if available
        if X_val is not None:
            X_val_flat = X_val.reshape(X_val.shape[0], -1)
            val_pred = self.model.predict(X_val_flat)
            val_mse = np.mean((val_pred - y_val) ** 2)
            val_mae = np.mean(np.abs(val_pred - y_val))
            results['val_loss'] = float(val_mse)
            results['val_mae'] = float(val_mae)

        return results

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using Random Forest"""
        if not self.is_trained:
            raise PredictionException("RandomForest", "Model not trained")

        X_flat = X.reshape(X.shape[0], -1)
        predictions = self.model.predict(X_flat)
        return predictions


class PredictionStrategyFactory:
    """Factory for creating prediction strategies"""

    @staticmethod
    def create_strategy(model_type: str, **kwargs) -> PredictionStrategy:
        """
        Create a prediction strategy

        Args:
            model_type: Type of model ('RNN', 'XGBoost', 'RandomForest')
            **kwargs: Model-specific parameters

        Returns:
            PredictionStrategy instance
        """
        strategies = {
            'RNN': RNNPredictionStrategy,
            'XGBoost': XGBoostPredictionStrategy,
            'RandomForest': RandomForestPredictionStrategy
        }

        if model_type not in strategies:
            raise ValueError(f"Unknown model type: {model_type}. Available: {list(strategies.keys())}")

        return strategies[model_type](**kwargs)

    @staticmethod
    def get_available_models() -> List[str]:
        """Get list of available model types"""
        return ['RNN', 'XGBoost', 'RandomForest']
