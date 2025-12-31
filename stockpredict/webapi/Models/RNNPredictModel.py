import darts

from Models.TimeSeriesPredict import TimeSeriesPredict
from darts.models.forecasting.rnn_model import RNNModel
from darts import concatenate
from darts.metrics import rmse
import os
class RNNPredictModel(TimeSeriesPredict):

    def __init__(self,*args):
        super(RNNPredictModel,self).__init__(args)
        self.model_sub_type = "LSTM"
        self.input_chunk_length = 14
        self.hidden_dim = 20
        self.n_rnn_layers = 1
        self.dropout = 0
        self.batch_size = 16
        self.n_epochs = 300
        self.learning_rate = 0.0001
        self.training_length = 30

        # Model storage directory - uses current working directory
        # Will be user's directory when created via UnifiedModelService
        self.model_storage_dir = os.getcwd()

        self.model = RNNModel(
            model=self.model_sub_type,
            hidden_dim=self.hidden_dim,
            dropout=self.dropout,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
            optimizer_kwargs={"lr": self.learning_rate},
            log_tensorboard=True,
            random_state=42,
            training_length=self.training_length,
            input_chunk_length=self.input_chunk_length,
            force_reset=True,
            save_checkpoints=True,
        )
    def getModelConfigurationParam(self):
        return {
                'model_sub_type':self.model_sub_type,
                'input_chunk_length':self.input_chunk_length,
                'hidden_dim':self.hidden_dim,
                'n_rnn_layers':self.n_rnn_layers,
                'dropout':self.dropout,
                'batch_size':self.batch_size,
                'n_epochs':self.n_epochs,
                'learning_rate':self.learning_rate,
                'training_length':self.training_length
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
                                   model_sub_type = "LSTM",
                                   input_chunk_length=14,
                                   hidden_dim=20,
                                   n_rnn_layers=1,
                                   dropout=0,
                                   batch_size=16,
                                   n_epochs=300,
                                   learning_rate=0.0001,
                                   training_length=20
                                   ):
        # CRITICAL: Cast all numeric parameters to correct types using safe conversion
        # Database JSON stores them as strings, but Darts needs int/float
        self.model_sub_type = str(model_sub_type) if model_sub_type else "LSTM"
        self.input_chunk_length = self._safe_int(input_chunk_length, 14)
        self.hidden_dim = self._safe_int(hidden_dim, 20)
        self.n_rnn_layers = self._safe_int(n_rnn_layers, 1)
        self.dropout = self._safe_float(dropout, 0)
        self.batch_size = self._safe_int(batch_size, 16)
        self.n_epochs = self._safe_int(n_epochs, 300)
        self.learning_rate = self._safe_float(learning_rate, 0.0001)
        self.training_length = self._safe_int(training_length, 20)

        # CRITICAL: Recreate the Darts RNNModel with updated parameters
        # Otherwise, the internal model still uses old parameters from __init__
        self.model = RNNModel(
            model=self.model_sub_type,
            hidden_dim=self.hidden_dim,
            dropout=self.dropout,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
            optimizer_kwargs={"lr": self.learning_rate},
            log_tensorboard=True,
            random_state=42,
            training_length=self.training_length,
            input_chunk_length=self.input_chunk_length,
            force_reset=True,
            save_checkpoints=True,
        )
    # train() method now inherited from parent class TimeSeriesPredict
    # No need to override unless model has special training requirements
    def predict(self,start_date,predict_length):
        super(RNNPredictModel, self).predict(start_date,predict_length)

        # Check if the model was trained with covariates
        # For torch models, check future_covariate_series (RNN only supports future covariates)
        model_uses_future_cov = getattr(self.model, 'future_covariate_series', None) is not None

        future_corvarates = None

        if model_uses_future_cov and hasattr(self, 'predict_future_covariates'):
            future_corvarates = self.predict_future_covariates
        elif hasattr(self, 'predict_future_covariates') and self.predict_future_covariates is not None:
            print(f"[PREDICT WARNING] Model was not trained with future covariates, ignoring provided future covariates")

        data = self.model.predict(int(predict_length),
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
        """Return RNN-specific parameters to save"""
        return {
            'model': self.model_sub_type,
            'hidden_dim': self.hidden_dim,
            'n_rnn_layers': self.n_rnn_layers,
            'dropout': self.dropout,
            'training_length': self.training_length,
            'optimizer_kwargs': {'lr': self.learning_rate}
        }

    def set_model_specific_params(self, model):
        """Restore RNN-specific parameters from loaded model"""
        self.model_sub_type = model.model_params.get('model')
        self.hidden_dim = model.model_params.get('hidden_dim')
        self.n_rnn_layers = model.model_params.get('n_rnn_layers')
        self.dropout = model.model_params.get('dropout')
        self.training_length = model.model_params.get('training_length')
        self.learning_rate = model.model_params.get('optimizer_kwargs', {}).get('lr')

    def get_model_class(self):
        """Return the RNN model class for loading"""
        return RNNModel

    # save_model() and load_model() now inherited from parent class TimeSeriesPredict
    def evaluate_model(self):
        p = self.target
        p = p[:-self.model.output_chunk_length]
        back_test = self.model.historical_forecasts(
            series=p,
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
















