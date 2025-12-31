from darts.models import NBEATSModel
from darts import concatenate
from darts.metrics import rmse
import os
from Models.TimeSeriesPredict import TimeSeriesPredict
class NBeatsPredictModel(TimeSeriesPredict):
    def __init__(self,*args):
        super(NBeatsPredictModel,self).__init__(args)
        self.set_model_type("NBeats")
        self.input_chunk_length = 14
        self.output_chunk_length = 10
        self.generic_architecture = True
        self.num_stacks = 10
        self.num_blocks=1
        self.num_layers=4
        self.layer_widths=512
        self.batch_size = 16
        self.n_epochs = 300
        self.nr_epochs_val_period=1
        self.model = NBEATSModel(
            input_chunk_length=self.input_chunk_length,
            output_chunk_length=self.output_chunk_length,
            generic_architecture=self.generic_architecture,
            num_stacks=self.num_stacks,
            num_blocks=self.num_blocks,
            num_layers=self.num_layers,
            layer_widths=self.layer_widths,
            n_epochs=self.n_epochs,
            nr_epochs_val_period=self.nr_epochs_val_period,
            batch_size=self.batch_size,
        )


    def getModelConfigurationParam(self):
        return {
            'input_chunk_length':self.input_chunk_length,
            'output_chunk_length': self.output_chunk_length,
            'generic_architecture': self.generic_architecture,
            'num_stacks': self.num_stacks,
            'num_blocks': self.num_blocks,
            'num_layers': self.num_layers,
            'layer_widths':self.layer_widths,
            'n_epochs':   self.n_epochs,
            'nr_epochs_val_period': self.nr_epochs_val_period,
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
                                   generic_architecture=True,
                                   num_stacks=10,
                                   num_blocks=1,
                                   num_layers=4,
                                   layer_widths=512,
                                   n_epochs=300,
                                   batch_size=16,
                                   nr_epochs_val_period=1
                                   ):
        self.input_chunk_length = self._safe_int(input_chunk_length, 14)
        self.output_chunk_length = self._safe_int(output_chunk_length, 10)
        self.generic_architecture = self._safe_bool(generic_architecture, True)
        self.num_stacks = self._safe_int(num_stacks, 10)
        self.num_blocks = self._safe_int(num_blocks, 1)
        self.num_layers = self._safe_int(num_layers, 4)
        self.layer_widths = self._safe_int(layer_widths, 512)
        self.batch_size = self._safe_int(batch_size, 16)
        self.n_epochs = self._safe_int(n_epochs, 300)
        self.nr_epochs_val_period = self._safe_int(nr_epochs_val_period, 1)
    # train() method now inherited from parent class TimeSeriesPredict
    # No need to override unless model has special training requirements
    def predict(self,start_date,predict_length):
        super(NBeatsPredictModel, self).predict(start_date, predict_length)

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
        """Return NBeats-specific parameters to save"""
        return {
            'generic_architecture': self.generic_architecture,
            'num_stacks': self.num_stacks,
            'num_blocks': self.num_blocks,
            'num_layers': self.num_layers,
            'layer_widths': self.layer_widths,
            'nr_epochs_val_period': self.nr_epochs_val_period
        }

    def set_model_specific_params(self, model):
        """Restore NBeats-specific parameters from loaded model"""
        self.generic_architecture = model.model_params.get('generic_architecture')
        self.num_stacks = model.model_params.get('num_stacks')
        self.num_blocks = model.model_params.get('num_blocks')
        self.num_layers = model.model_params.get('num_layers')
        self.layer_widths = model.model_params.get('layer_widths')
        self.nr_epochs_val_period = model.model_params.get('nr_epochs_val_period')

    def get_model_class(self):
        """Return the NBeats model class for loading"""
        return NBEATSModel

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