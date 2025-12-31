from darts.models import TransformerModel, ExponentialSmoothing
from darts import concatenate
from darts.metrics import rmse
import os
from Models.TimeSeriesPredict import TimeSeriesPredict
class TransformerPredictModel(TimeSeriesPredict):
    def __init__(self,*args):
        super(TransformerPredictModel,self).__init__(args)

        self.set_model_type("Transfomer")
        self.input_chunk_length = 14
        self.output_chunk_length = 10
        self.batch_size = 16
        self.n_epochs=300
        self.nr_epochs_val_period = 10
        self.d_model=16
        self.nhead=8
        self.num_encoder_layers=2
        self.num_decoder_layers=2
        self.dim_feedforward=128
        self.dropout = 0.1
        self.activation = 'relu'
        self.random_state=42
        self.save_checkpoints = True
        self.force_reset = True
        self.model = TransformerModel(
            input_chunk_length=self.input_chunk_length,
            output_chunk_length=self.output_chunk_length,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
            nr_epochs_val_period=self.nr_epochs_val_period,
            d_model=self.d_model,
            nhead=self.nhead,
            num_encoder_layers=self.num_encoder_layers,
            num_decoder_layers=self.num_decoder_layers,
            dim_feedforward=self.dim_feedforward,
            dropout=self.dropout,
            activation=self.activation,
            random_state=self.random_state,
            save_checkpoints=self.save_checkpoints,
            force_reset=self.force_reset
        )

    def getModelConfigurationParam(self):
        return {
            'input_chunk_length':self.input_chunk_length,
            'output_chunk_length':self.output_chunk_length,
            'batch_size':self.batch_size,
            'n_epochs': self.n_epochs,
            'nr_epochs_val_period':self.nr_epochs_val_period,
            'd_model':self.d_model,
            'nhead':self.nhead,
            'num_encoder_layers':self.num_encoder_layers,
            'num_decoder_layers':self.num_decoder_layers,
            'dim_feedforward':self.dim_feedforward,
            'dropout':self.dropout,
            'activation':self.activation,
            'random_state':self.random_state,
            'save_checkpoints':self.save_checkpoints,
            'force_reset':self.force_reset

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
                                   batch_size = 16,
                                   n_epochs = 200,
                                   nr_epochs_val_period = 10,
                                   d_model = 16,
                                   nhead = 8,
                                   num_encoder_layers = 2,
                                   num_decoder_layers = 2,
                                   dim_feedforward = 128,
                                   dropout = 0.1,
                                   activation = 'relu',
                                   random_state = 42,
                                   save_checkpoints = True,
                                   force_reset = True
                                   ):
        self.input_chunk_length = self._safe_int(input_chunk_length, 14)
        self.output_chunk_length = self._safe_int(output_chunk_length, 10)
        self.batch_size = self._safe_int(batch_size, 16)
        self.n_epochs = self._safe_int(n_epochs, 200)
        self.nr_epochs_val_period = self._safe_int(nr_epochs_val_period, 10)
        self.d_model = self._safe_int(d_model, 16)
        self.nhead = self._safe_int(nhead, 8)
        self.num_encoder_layers = self._safe_int(num_encoder_layers, 2)
        self.num_decoder_layers = self._safe_int(num_decoder_layers, 2)
        self.dim_feedforward = self._safe_int(dim_feedforward, 128)
        self.dropout = self._safe_float(dropout, 0.1)
        self.activation = activation
        self.random_state = self._safe_int(random_state, 42)
        self.save_checkpoints = self._safe_bool(save_checkpoints, True)
        self.force_reset = self._safe_bool(force_reset, True)
    # train() method now inherited from parent class TimeSeriesPredict
    # No need to override unless model has special training requirements
    def predict(self,start_date, predict_length):
        super(TransformerPredictModel, self).predict(start_date, predict_length)

        # Check if the model was trained with covariates
        # For torch models, check past_covariate_series
        model_uses_past_cov = getattr(self.model, 'past_covariate_series', None) is not None

        past_corvarites = None

        if model_uses_past_cov and hasattr(self, 'predict_past_covariates'):
            past_corvarites = self.predict_past_covariates
        elif hasattr(self, 'predict_past_covariates') and self.predict_past_covariates is not None:
            print(f"[PREDICT WARNING] Model was not trained with past covariates, ignoring provided past covariates")

        data = self.model.predict(int(predict_length),
                                  past_covariates=past_corvarites,
                                  )
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
        """Return Transformer-specific parameters to save"""
        return {
            'nr_epochs_val_period': self.nr_epochs_val_period,
            'd_model': self.d_model,
            'nhead': self.nhead,
            'num_encoder_layers': self.num_encoder_layers,
            'num_decoder_layers': self.num_decoder_layers,
            'dim_feedforward': self.dim_feedforward,
            'dropout': self.dropout,
            'activation': self.activation,
            'random_state': self.random_state,
            'save_checkpoints': self.save_checkpoints,
            'force_reset': self.force_reset
        }

    def set_model_specific_params(self, model):
        """Restore Transformer-specific parameters from loaded model"""
        self.nr_epochs_val_period = model.model_params.get('nr_epochs_val_period')
        self.d_model = model.model_params.get('d_model')
        self.nhead = model.model_params.get('nhead')
        self.num_encoder_layers = model.model_params.get('num_encoder_layers')
        self.num_decoder_layers = model.model_params.get('num_decoder_layers')
        self.dim_feedforward = model.model_params.get('dim_feedforward')
        self.dropout = model.model_params.get('dropout')
        self.activation = model.model_params.get('activation')
        self.random_state = model.model_params.get('random_state')
        self.save_checkpoints = model.save_checkpoints
        self.force_reset = model.model_params.get('force_reset')

    def get_model_class(self):
        """Return the Transformer model class for loading"""
        return TransformerModel

    # save_model() and load_model() now inherited from parent class TimeSeriesPredict
    def evaluate_model(self):
        back_test = self.model.historical_forecasts(
            series=self.target,
            past_covariates=self.past_multi if hasattr(self, 'past_multi') else None,
            start=0.8,
            retrain=False,
            verbose=True,
            forecast_horizon=10
        )
        return rmse(self.target,back_test)
    def get_latest_training_date(self):
        if self.model.training_series != None:
            return self.model.training_series.end_time()
    def get_chunk_length(self):
        return self.input_chunk_length