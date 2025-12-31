from darts.models import NHiTSModel
from darts import concatenate
from darts.metrics import rmse
import os
from Models.TimeSeriesPredict import TimeSeriesPredict
class NHitsPredictModel(TimeSeriesPredict):
    def __init__(self,*args):
        super(NHitsPredictModel,self).__init__(args)
        self.set_model_type("NHits")
        self.input_chunk_length = 14
        self.output_chunk_length = 10
        self.num_stacks = 3
        self.num_blocks=1
        self.num_layers=2
        self.layer_widths=512
        self.pooling_kernel_sizes = None
        self.n_freq_downsample = None
        self.dropout = 0.1
        self.activation = 'ReLU'
        self.MaxPool1d = True
        self.batch_size = 16
        self.n_epochs = 300
        self.nr_epochs_val_period=1
        self.model = NHiTSModel(
            input_chunk_length=self.input_chunk_length,
            output_chunk_length=self.output_chunk_length,
            num_stacks=self.num_stacks,
            num_blocks=self.num_blocks,
            num_layers=self.num_layers,
            layer_widths=self.layer_widths,
            pooling_kernel_sizes=self.pooling_kernel_sizes,
            n_freq_downsample=self.n_freq_downsample,
            dropout=self.dropout,
            activation=self.activation,
            MaxPool1d=self.MaxPool1d,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
        )



    def getModelConfigurationParam(self):
        return {
            'input_chunk_length':self.input_chunk_length,
            'output_chunk_length': self.output_chunk_length,
            'num_stacks': self.num_stacks,
            'num_blocks': self.num_blocks,
            'num_layers': self.num_layers,
            'layer_widths':self.layer_widths,
            'pooling_kernel_sizes':self.pooling_kernel_sizes,
            'n_freq_downsample':self.n_freq_downsample,
            'dropout':self.dropout,
            'activation':self.activation,
            'MaxPool1d':self.MaxPool1d,
            'n_epochs':   self.n_epochs,
            'batch_size': self.batch_size,
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
                                   num_stacks=10,
                                   num_blocks=1,
                                   num_layers=4,
                                   layer_widths=512,
                                   pooling_kernel_sizes = None,
                                   n_freq_downsample = None,
                                   dropout = 0.1,
                                   activation = 'ReLU',
                                   MaxPool1d = True,
                                   n_epochs=300,
                                   batch_size=16,

                                   ):
        self.input_chunk_length = self._safe_int(input_chunk_length, 14)
        self.output_chunk_length = self._safe_int(output_chunk_length, 10)
        self.num_stacks = self._safe_int(num_stacks, 10)
        self.num_blocks = self._safe_int(num_blocks, 1)
        self.num_layers = self._safe_int(num_layers, 4)
        self.layer_widths = self._safe_int(layer_widths, 512)
        self.pooling_kernel_sizes = pooling_kernel_sizes
        self.n_freq_downsample = n_freq_downsample
        self.dropout = self._safe_float(dropout, 0.1)
        self.activation = activation
        self.batch_size = self._safe_int(batch_size, 16)
        self.n_epochs = self._safe_int(n_epochs, 300)
        self.MaxPool1d = self._safe_bool(MaxPool1d, True)
    # train() method now inherited from parent class TimeSeriesPredict
    # No need to override unless model has special training requirements
    def predict(self,start_date,predict_length):
        super(NHitsPredictModel, self).predict(start_date, predict_length)

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
        """Return NHits-specific parameters to save"""
        return {
            'num_stacks': self.num_stacks,
            'num_blocks': self.num_blocks,
            'num_layers': self.num_layers,
            'layer_widths': self.layer_widths,
            'pooling_kernel_sizes': self.pooling_kernel_sizes,
            'n_freq_downsample': self.n_freq_downsample,
            'dropout': self.dropout,
            'activation': self.activation,
            'MaxPool1d': self.MaxPool1d
        }

    def set_model_specific_params(self, model):
        """Restore NHits-specific parameters from loaded model"""
        self.num_stacks = model.model_params.get('num_stacks')
        self.num_blocks = model.model_params.get('num_blocks')
        self.num_layers = model.model_params.get('num_layers')
        self.layer_widths = model.model_params.get('layer_widths')
        self.pooling_kernel_sizes = model.model_params.get('pooling_kernel_sizes')
        self.n_freq_downsample = model.model_params.get('n_freq_downsample')
        self.dropout = model.model_params.get('dropout')
        self.activation = model.model_params.get('activation')
        self.MaxPool1d = model.model_params.get('MaxPool1d')

    def get_model_class(self):
        """Return the NHits model class for loading"""
        return NHiTSModel

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