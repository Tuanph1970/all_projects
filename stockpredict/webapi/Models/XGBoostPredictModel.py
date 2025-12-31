from darts.models.forecasting.xgboost import XGBModel
from darts import concatenate
from Models.TimeSeriesPredict import TimeSeriesPredict
import os
from darts.metrics import rmse
class XGBootsPredictModel(TimeSeriesPredict):
    def __init__(self,*args):
        super(XGBootsPredictModel,self).__init__(args)
        self.set_model_type("XGBoots")
        self.lag_len = 14
        self.lag_past_len = 14
        self.lag_future_len = 14
        self.output_chunk_length = 1
        self.add_encoders=None
        self.likelihood = None
        self.quantiles = None
        self.random_state = None
        self.multi_models=True
        self.use_static_covariates=False
        self.lags = []
        for i in range(self.lag_len, 0, -1):
            self.lags.append(-i)
        self.lags_past_covariates = []
        for i in range(self.lag_past_len, 0, -1):
            self.lags_past_covariates.append(-i)
        self.lags_future_covariates = []
        for i in range(self.lag_future_len, 0, -1):
            self.lags_future_covariates.append(-i)

        # IMPORTANT: Only pass lags_past_covariates/lags_future_covariates to model initialization
        # if we will actually provide the corresponding covariate data during training.
        # Passing lags without data causes ValueError. We'll set these dynamically before training.
        self.model = XGBModel(
            lags=self.lags,
            lags_past_covariates=None,  # Will be set before training if past covariates exist
            lags_future_covariates=None,  # Will be set before training if future covariates exist
            output_chunk_length=self.output_chunk_length,
            add_encoders=self.add_encoders,
            likelihood=self.likelihood,
            quantiles=self.quantiles,
            random_state=self.random_state,
            multi_models=self.multi_models,
            use_static_covariates=self.use_static_covariates,
        )


    def getModelConfigurationParam(self):
        return {
            'lag_len': self.lag_len,
            'lag_past_len': self.lag_past_len,
            'lag_future_len': self.lag_future_len,
            'output_chunk_length': self.output_chunk_length,
            'add_encoders': self.add_encoders,
            'likelihood': self.likelihood,
            'quantiles': self.quantiles,
            'multi_models': self.multi_models,
            'use_static_covariates': self.use_static_covariates,

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
                                   lag_len=14,
                                   lag_past_len=14,
                                   lag_future_len=14,
                                   output_chunk_length = 1,
                                   add_encoders = None,
                                   likelihood = None,
                                   quantiles = None,
                                   multi_models = True,
                                   use_static_covariates = True,


                                   ):
        self.lag_len = self._safe_int(lag_len, 14)
        self.lag_past_len = self._safe_int(lag_past_len, 14)
        self.lag_future_len = self._safe_int(lag_future_len, 14)
        self.lags = []
        for i in range(self.lag_len, 0, -1):
            self.lags.append(-i)
        self.lags_past_covariates = []
        for i in range(self.lag_past_len, 0, -1):
            self.lags_past_covariates.append(-i)
        self.lags_future_covariates = []
        for i in range(self.lag_future_len, 0, -1):
            self.lags_future_covariates.append(-i)
        self.output_chunk_length = self._safe_int(output_chunk_length, 1)
        self.add_encoders = add_encoders
        self.likelihood = likelihood
        self.quantiles = quantiles
        self.multi_models = self._safe_bool(multi_models, True)
        self.use_static_covariates = self._safe_bool(use_static_covariates, True)
    # train() method now inherited from parent class TimeSeriesPredict
    # No need to override unless model has special training requirements
    def predict(self,start_date, predict_length):
        super(XGBootsPredictModel, self).predict(start_date, predict_length)

        # Check if the model was trained with covariates by examining the model's lags parameters
        # Only pass covariates that the model was actually trained on to avoid mismatch errors
        model_uses_past_cov = getattr(self.model, 'lags_past_covariates', None) is not None
        model_uses_future_cov = getattr(self.model, 'lags_future_covariates', None) is not None

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

        # For sklearn-based models (XGBoost, CatBoost, etc.), we must provide the 'series' parameter
        # when calling predict() on a loaded model, as these models don't store training series internally
        data = self.model.predict(int(predict_length),
                                  series=self.predict_target,
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
        """Return XGBoost-specific parameters to save"""
        return {
            'lags': self.lags,
            'lags_past_covariates': self.lags_past_covariates,
            'lags_future_covariates': self.lags_future_covariates,
            'multi_models': self.multi_models,
            'likelihood': self.likelihood,
            'quantiles': self.quantiles,
            'uses_static_covariates': self.use_static_covariates
        }

    def set_model_specific_params(self, model):
        """Restore XGBoost-specific parameters from loaded model"""
        self.lags = model.model_params.get('lags', [])
        self.lags_past_covariates = model.model_params.get('lags_past_covariates', [])
        self.lags_future_covariates = model.model_params.get('lags_future_covariates', [])
        self.lag_len = len(self.lags) if self.lags else 14
        self.lag_past_len = len(self.lags_past_covariates) if self.lags_past_covariates else 14
        self.lag_future_len = len(self.lags_future_covariates) if self.lags_future_covariates else 14
        self.add_encoders = model.model_params.get('add_encoders')
        self.likelihood = model.model_params.get('likelihood')
        self.quantiles = model.model_params.get('quantiles')
        self.multi_models = model.model_params.get('multi_models')
        self.use_static_covariates = model.model_params.get('use_static_covariates')

    def get_model_class(self):
        """Return the XGBoost model class for loading"""
        return XGBModel

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
        return max(self.output_chunk_length,self.lag_len)