from darts.models.forecasting.tft_model import TFTModel
from darts import concatenate
from darts.utils.likelihood_models import QuantileRegression
from darts.metrics import rmse
import os
from Models.TimeSeriesPredict import TimeSeriesPredict
class TFTPredictModel(TimeSeriesPredict):
    def __init__(self,*args):
        super(TFTPredictModel,self).__init__(args)
        self.set_model_type("Temporal Fusion Transformer")
        self.input_chunk_length = 24
        self.output_chunk_length = 12
        self.hidden_size = 64
        self.lstm_layers = 1
        self.num_attention_heads = 4
        self.dropout = 0.1
        self.batch_size = 16
        self.n_epochs=300
        self.add_relative_index=False
        self.add_encoders=None
        self.random_state=42
        quantiles = [
            0.01,
            0.05,
            0.1,
            0.15,
            0.2,
            0.25,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.75,
            0.8,
            0.85,
            0.9,
            0.95,
            0.99,
        ]
        self.model = TFTModel(
            input_chunk_length=self.input_chunk_length,
            output_chunk_length=self.output_chunk_length,
            hidden_size=self.hidden_size,
            lstm_layers=self.lstm_layers,
            num_attention_heads=self.num_attention_heads,
            dropout=self.dropout,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
            add_relative_index=self.add_relative_index,
            add_encoders=self.add_encoders,
            likelihood=QuantileRegression(
                quantiles=quantiles
            ),
            random_state=self.random_state
        )

    def getModelConfigurationParam(self):
        return {
            'input_chunk_length':self.input_chunk_length,
            'output_chunk_length':self.output_chunk_length,
            'hidden_size': self.hidden_size,
            'lstm_layers':self.lstm_layers,
            'num_attention_heads':self.num_attention_heads,
            'dropout':self.dropout,
            'batch_size':self.batch_size,
            'n_epochs': self.n_epochs,
            'add_relative_index':self.add_relative_index,
            'add_encoders':self.add_encoders,
            'random_state':self.random_state
        }
    def _safe_int(self, value, default):
        """Safely convert value to int, returning default if conversion fails."""
        if value is None:
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return default
        return default

    def _safe_float(self, value, default):
        """Safely convert value to float, returning default if conversion fails."""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        return default

    def _safe_bool(self, value, default):
        """Safely convert value to bool, handling string 'true'/'false' from JSON."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() == 'true'
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    def setModelConfigurationParam(self,
                                   input_chunk_length=14,
                                   output_chunk_length=10,
                                   hidden_size = 64,
                                   lstm_layers = 1,
                                   num_attention_heads = 4,
                                   dropout = 0.1,
                                   batch_size = 16,
                                   n_epochs = 300,
                                   add_relative_index = False,
                                   add_encoders = None,
                                   random_state = 42
                                   ):
        self.input_chunk_length = self._safe_int(input_chunk_length, 14)
        self.output_chunk_length = self._safe_int(output_chunk_length, 10)
        self.hidden_size = self._safe_int(hidden_size, 64)
        self.lstm_layers = self._safe_int(lstm_layers, 1)
        self.num_attention_heads = self._safe_int(num_attention_heads, 4)
        self.dropout = self._safe_float(dropout, 0.1)
        self.batch_size = self._safe_int(batch_size, 16)
        self.n_epochs = self._safe_int(n_epochs, 300)
        self.add_relative_index = self._safe_bool(add_relative_index, False)
        self.add_encoders = add_encoders
        self.random_state = self._safe_int(random_state, 42)


    # train() method now inherited from parent class TimeSeriesPredict
    # No need to override unless model has special training requirements
    def predict(self, start_date, predict_length):
        super(TFTPredictModel, self).predict(start_date, predict_length)

        # Check if the model was trained with covariates
        # For torch models, check past_covariate_series and future_covariate_series
        model_uses_past_cov = getattr(self.model, 'past_covariate_series', None) is not None
        model_uses_future_cov = getattr(self.model, 'future_covariate_series', None) is not None

        past_corvarites = None
        future_corvarates = None

        if model_uses_past_cov and hasattr(self, 'predict_past_covariates'):
            past_corvarites = self.predict_past_covariates
        elif hasattr(self, 'predict_past_covariates') and self.predict_past_covariates is not None:
            print(f"[PREDICT WARNING] Model was not trained with past covariates, ignoring provided past covariates")

        if model_uses_future_cov and hasattr(self, 'predict_future_covariates'):
            future_corvarates = self.predict_future_covariates
        elif hasattr(self, 'predict_future_covariates') and self.predict_future_covariates is not None:
            print(f"[PREDICT WARNING] Model was not trained with future covariates, ignoring provided future covariates")

        data = self.model.predict(int(predict_length),
                                  past_covariates=past_corvarites,
                                  future_covariates=future_corvarates)
        scaler = self.target_series.get_scaler()
        data = scaler.inverse_transform(data)
        time_index = data.time_index
        values = data.values(copy=True)
        json_result = []
        for i in range(len(time_index)):
            json_obj = dict()
            json_obj['tradingdate'] = time_index[i]
            json_obj['close'] = values[i][0]
            json_result.append(json_obj)
        return json_result
    # Override hook methods for model-specific parameters
    def get_model_specific_params(self):
        """Return TFT-specific parameters to save"""
        return {
            'hidden_size': self.hidden_size,
            'lstm_layers': self.lstm_layers,
            'num_attention_heads': self.num_attention_heads,
            'dropout': self.dropout,
            'add_relative_index': self.add_relative_index,
            'add_encoders': self.add_encoders,
            'random_state': self.random_state
        }

    def set_model_specific_params(self, model):
        """Restore TFT-specific parameters from loaded model"""
        self.hidden_size = model.model_params.get('hidden_size')
        self.lstm_layers = model.model_params.get('lstm_layers')
        self.num_attention_heads = model.model_params.get('num_attention_heads')
        self.dropout = model.model_params.get('dropout')
        self.add_relative_index = model.model_params.get('add_relative_index')
        self.add_encoders = model.model_params.get('add_encoders')
        self.random_state = model.model_params.get('random_state')

    def get_model_class(self):
        """Return the TFT model class for loading"""
        return TFTModel

    # save_model() and load_model() now inherited from parent class TimeSeriesPredict
    def evaluate_model(self):
        p = self.target
        p = p[:-self.model.output_chunk_length]
        back_test = self.model.historical_forecasts(
            series=p,
            past_covariates=self.past_multi if hasattr(self, 'past_multi') else None,
            future_covariates=self.future_multi if hasattr(self, 'future_multi') else None,
            start=0.8,
            retrain=False,
            verbose=True,
            forecast_horizon=self.model.output_chunk_length
        )
        return rmse(self.target,back_test)
    def get_latest_training_date(self):
        if self.model.training_series != None:
            return self.model.training_series.end_time()
    def get_chunk_length(self):
        return self.input_chunk_length