from darts.models import TiDEModel
import torch
from darts import concatenate
from darts.metrics import rmse
import os
from Models.TimeSeriesPredict import TimeSeriesPredict
class TimeDeepEncoderPredictModel(TimeSeriesPredict):
    def __init__(self,*args):
        super(TimeDeepEncoderPredictModel,self).__init__(args)
        self.set_model_type("TiDe")
        self.learning_rate = 0.001
        self.gradient_clip_val = 1
        self.max_epochs = 200
        self.accelerator = "auto"
        self.callbacks = []
        self.gamma = 0.999
        self.monitor= "val_loss"
        self.patience =  10
        self.min_delta = 0.001
        self.mode =  "min"
        self.input_chunk_length = 12
        self.output_chunk_length = 12
        self.likelihood = None
        self.save_checkpoints = True
        self.force_reset = True
        self.batch_size = 256
        self.random_state = 42
        self.use_reversible_instance_norm = False
        optimizer_kwargs = {
            "lr": self.learning_rate,
        }
        pl_trainer_kwargs = {
            "gradient_clip_val": self.gradient_clip_val,
            "max_epochs": self.max_epochs,
            "accelerator": self.accelerator,
            "callbacks": self.callbacks,
        }
        lr_scheduler_cls = torch.optim.lr_scheduler.ExponentialLR
        lr_scheduler_kwargs = {
            "gamma": self.gamma,
        }
        early_stopping_args = {
            "monitor": self.monitor,
            "patience": self.patience,
            "min_delta": self.min_delta,
            "mode": self.mode,
        }
        common_model_args = {
            "input_chunk_length": self.input_chunk_length,
            "output_chunk_length": self.output_chunk_length,
            "optimizer_kwargs": optimizer_kwargs,
            "pl_trainer_kwargs": pl_trainer_kwargs,
            "lr_scheduler_cls": lr_scheduler_cls,
            "lr_scheduler_kwargs": lr_scheduler_kwargs,
            "likelihood": self.likelihood,
            "save_checkpoints": self.save_checkpoints,
            "force_reset": self.force_reset,
            "batch_size": self.batch_size,
            "random_state": self.random_state,
        }
        self.model = TiDEModel(
            **common_model_args,
            use_reversible_instance_norm=self.use_reversible_instance_norm

        )
    def getModelConfigurationParam(self):
        return {
            'learning_rate':self.learning_rate,
            'gradient_clip_val':self.gradient_clip_val,
            'max_epochs':self.max_epochs,
            'accelerator':self.accelerator,
            'callbacks':self.callbacks,
            'gamma':self.gamma,
            'monitor':self.monitor,
            'patience':self.patience,
            'min_delta':self.min_delta,
            'mode':self.mode,
            'input_chunk_length':self.input_chunk_length,
            'output_chunk_length':self.output_chunk_length,
            'likelihood':self.likelihood,
            'save_checkpoints':self.save_checkpoints,
            'force_reset':self.force_reset,
            'batch_size':self.batch_size,
            'random_state':self.random_state,
            'use_reversible_instance_norm':self.use_reversible_instance_norm
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
                    learning_rate = 0.001,
                    gradient_clip_val = 1,
                    max_epochs = 200,
                    accelerator = "auto",
                    callbacks = [],
                    gamma = 0.999,
                    monitor = "val_loss",
                    patience = 10,
                    min_delta = 0.001,
                    mode = "min",
                    input_chunk_length = int(12),
                    output_chunk_length = int(12),
                    likelihood = None,
                    save_checkpoints = True,
                    force_reset = True,
                    batch_size = int(256),
                    random_state = int(42),
                    use_reversible_instance_norm = False
                                   ):
        self.learning_rate = self._safe_float(learning_rate, 0.001)
        self.gradient_clip_val = self._safe_int(gradient_clip_val, 1)
        self.max_epochs = self._safe_int(max_epochs, 200)
        self.accelerator = accelerator
        self.callbacks = callbacks if callbacks else []
        self.gamma = self._safe_float(gamma, 0.999)
        self.monitor = monitor
        self.patience = self._safe_int(patience, 10)
        self.min_delta = self._safe_float(min_delta, 0.001)
        self.mode = mode
        self.input_chunk_length = self._safe_int(input_chunk_length, 12)
        self.output_chunk_length = self._safe_int(output_chunk_length, 12)
        self.likelihood = likelihood
        self.save_checkpoints = self._safe_bool(save_checkpoints, True)
        self.force_reset = self._safe_bool(force_reset, True)
        self.batch_size = self._safe_int(batch_size, 256)
        self.random_state = self._safe_int(random_state, 42)
        self.use_reversible_instance_norm = self._safe_bool(use_reversible_instance_norm, False)

    # train() method now inherited from parent class TimeSeriesPredict
    # No need to override unless model has special training requirements
    def predict(self,start_date, predict_length):
        super(TimeDeepEncoderPredictModel, self).predict(start_date, predict_length)

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
        """Return TiDE-specific parameters to save"""
        return {
            'optimizer_kwargs': {'lr': self.learning_rate},
            'pl_trainer_kwargs': {
                'gradient_clip_val': self.gradient_clip_val,
                'max_epochs': self.max_epochs,
                'accelerator': self.accelerator,
                'callbacks': self.callbacks
            },
            'lr_scheduler_kwargs': {'gamma': self.gamma},
            'likelihood': self.likelihood,
            'save_checkpoints': self.save_checkpoints,
            'force_reset': self.force_reset,
            'random_state': self.random_state,
            'use_reversible_instance_norm': self.use_reversible_instance_norm
        }

    def set_model_specific_params(self, model):
        """Restore TiDE-specific parameters from loaded model"""
        self.learning_rate = model.model_params.get('optimizer_kwargs', {}).get('lr')
        pl_trainer = model.model_params.get('pl_trainer_kwargs', {})
        self.gradient_clip_val = pl_trainer.get('gradient_clip_val')
        self.max_epochs = pl_trainer.get('max_epochs')
        self.accelerator = pl_trainer.get('accelerator')
        self.callbacks = pl_trainer.get('callbacks')
        self.gamma = model.model_params.get('lr_scheduler_kwargs', {}).get('gamma')
        self.likelihood = model.model_params.get('likelihood')
        self.save_checkpoints = model.model_params.get('save_checkpoints')
        self.force_reset = model.model_params.get('force_reset')
        self.random_state = model.model_params.get('random_state')
        self.use_reversible_instance_norm = model.model_params.get('use_reversible_instance_norm')

    def get_model_class(self):
        """Return the TiDE model class for loading"""
        return TiDEModel

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