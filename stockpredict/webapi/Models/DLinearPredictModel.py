from darts.models.forecasting.dlinear import DLinearModel
from darts import concatenate
import os
from darts.metrics import rmse
from Models.TimeSeriesPredict import TimeSeriesPredict
class DLinearPredictModel(TimeSeriesPredict):
    def __init__(self,*args):
        super(DLinearPredictModel,self).__init__(args)
        self.set_model_type("DLinear")
        self.input_chunk_length = 14
        self.output_chunk_length = 10
        self.shared_weights=False
        self.kernel_size=25
        self.const_init=True
        self.use_static_covariates=False
        self.batch_size=32
        self.n_epochs = 100
        self.model = DLinearModel(
            input_chunk_length=self.input_chunk_length,
            output_chunk_length=self.output_chunk_length,
            shared_weights=self.shared_weights,
            kernel_size=self.kernel_size,
            const_init=self.const_init,
            use_static_covariates=self.use_static_covariates,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
        )
    def getModelConfigurationParam(self):
        return {
            'input_chunk_length':self.input_chunk_length,
            'output_chunk_length':self.output_chunk_length,
            'shared_weights': self.shared_weights,
            'kernel_size':self.kernel_size,
            'const_init': self.const_init,
             'use_static_covariates':self.use_static_covariates,
            'batch_size': self.batch_size,
            'n_epochs': self.n_epochs,
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
                                   shared_weights = False,
                                   kernel_size = 25,
                                   const_init = True,
                                   use_static_covariates = False,
                                   batch_size = 16,
                                   n_epochs = 200,

                                   ):
        # CRITICAL: Cast all parameters to correct types using safe conversion
        self.input_chunk_length = self._safe_int(input_chunk_length, 14)
        self.output_chunk_length = self._safe_int(output_chunk_length, 10)
        self.shared_weights = self._safe_bool(shared_weights, False)
        self.kernel_size = self._safe_int(kernel_size, 25)
        self.const_init = self._safe_bool(const_init, True)
        self.use_static_covariates = self._safe_bool(use_static_covariates, False)
        self.batch_size = self._safe_int(batch_size, 16)
        self.n_epochs = self._safe_int(n_epochs, 200)

        # CRITICAL: Recreate the Darts model with updated parameters
        self.model = DLinearModel(
            input_chunk_length=self.input_chunk_length,
            output_chunk_length=self.output_chunk_length,
            shared_weights=self.shared_weights,
            kernel_size=self.kernel_size,
            const_init=self.const_init,
            use_static_covariates=self.use_static_covariates,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
        )


    # train() method now inherited from parent class TimeSeriesPredict
    # No need to override unless model has special training requirements
    def predict(self,start_date,predict_length):
        super(DLinearPredictModel, self).predict(start_date, predict_length)

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
        """Return DLinear-specific parameters to save"""
        return {
            'shared_weights': self.shared_weights,
            'kernel_size': self.kernel_size,
            'const_init': self.const_init,
            'uses_static_covariates': self.use_static_covariates
        }

    def set_model_specific_params(self, model):
        """Restore DLinear-specific parameters from loaded model"""
        self.shared_weights = model.model_params.get('shared_weights')
        self.kernel_size = model.model_params.get('kernel_size')
        self.const_init = model.model_params.get('const_init')
        self.use_static_covariates = model.uses_static_covariates

    def get_model_class(self):
        """Return the DLinear model class for loading"""
        return DLinearModel

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
