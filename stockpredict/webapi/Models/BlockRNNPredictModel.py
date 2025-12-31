
from Models.TimeSeriesPredict import TimeSeriesPredict
from darts.models.forecasting.block_rnn_model import BlockRNNModel
from darts import concatenate
from darts.metrics import rmse
import os
class BlockRNNPredictModel(TimeSeriesPredict):

    def __init__(self,*args):
        super(BlockRNNPredictModel,self).__init__(args)
        self.model_sub_type = "LSTM"
        self.input_chunk_length = 14
        self.hidden_dim = 20
        self.n_rnn_layers = 1
        self.dropout = 0
        self.batch_size = 16
        self.n_epochs = 300
        self.learning_rate = 0.0001
        self.output_chunk_length = 10

        # Model storage directory - uses current working directory
        # Will be user's directory when created via UnifiedModelService
        self.model_storage_dir = os.getcwd()

        # Work directory for training checkpoints - uses current working directory
        # This prevents Darts from creating separate subdirectories
        self.work_dir = os.getcwd()

        self.model = BlockRNNModel(
            model=self.model_sub_type,
            hidden_dim=self.hidden_dim,
            dropout=self.dropout,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
            optimizer_kwargs={"lr": self.learning_rate},
            log_tensorboard=True,
            random_state=42,
            input_chunk_length=self.input_chunk_length,
            output_chunk_length=self.output_chunk_length,
            force_reset=True,
            save_checkpoints=True,
            work_dir=self.work_dir
        )
    def getModelConfigurationParam(self):
        return {
                'model_sub_type': self.model_sub_type,
                'input_chunk_length':self.input_chunk_length,
                'hidden_dim':self.hidden_dim,
                'n_rnn_layers':self.n_rnn_layers,
                'dropout':self.dropout,
                'batch_size':self.batch_size,
                'n_epochs':self.n_epochs,
                'learning_rate':self.learning_rate,

                'output_chunk_length':self.output_chunk_length,
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
                                   output_chunk_length=10,
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
        self.output_chunk_length = self._safe_int(output_chunk_length, 10)

        # CRITICAL: Recreate the Darts BlockRNNModel with updated parameters
        # Otherwise, the internal model still uses old parameters from __init__
        self.model = BlockRNNModel(
            model=self.model_sub_type,
            hidden_dim=self.hidden_dim,
            dropout=self.dropout,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
            optimizer_kwargs={"lr": self.learning_rate},
            log_tensorboard=True,
            random_state=42,
            input_chunk_length=self.input_chunk_length,
            output_chunk_length=self.output_chunk_length,
            force_reset=True,
            save_checkpoints=True,
            work_dir=self.work_dir
        )
    # train() method now inherited from parent class TimeSeriesPredict
    # No need to override unless model has special training requirements
    def predict(self,start_date,predict_length):
        super(BlockRNNPredictModel, self).predict(start_date, predict_length)

        # Check if the model was trained with covariates
        # For torch models, check past_covariate_series (BlockRNN only supports past covariates)
        model_uses_past_cov = getattr(self.model, 'past_covariate_series', None) is not None

        past_corvarites = None

        if model_uses_past_cov and hasattr(self, 'predict_past_covariates'):
            past_corvarites = self.predict_past_covariates
        elif hasattr(self, 'predict_past_covariates') and self.predict_past_covariates is not None:
            print(f"[PREDICT WARNING] Model was not trained with past covariates, ignoring provided past covariates")

        data = self.model.predict(int(predict_length),
                                  past_covariates=past_corvarites)
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
        """Return BlockRNN-specific parameters to save"""
        return {
            'model': self.model_sub_type,
            'hidden_dim': self.hidden_dim,
            'n_rnn_layers': self.n_rnn_layers,
            'dropout': self.dropout,
            'optimizer_kwargs': {'lr': self.learning_rate}
        }

    def set_model_specific_params(self, model):
        """Restore BlockRNN-specific parameters from loaded model"""
        self.model_sub_type = model.model_params.get('model')
        self.hidden_dim = model.model_params.get('hidden_dim')
        self.n_rnn_layers = model.model_params.get('n_rnn_layers')
        self.dropout = model.model_params.get('dropout')
        self.learning_rate = model.model_params.get('optimizer_kwargs', {}).get('lr')

    def get_model_class(self):
        """Return the BlockRNN model class for loading"""
        return BlockRNNModel

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











