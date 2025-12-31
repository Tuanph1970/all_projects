import mysql.connector as connection
import pandas as pd
import os
import darts
from darts import TimeSeries
from darts.dataprocessing.transformers import Scaler
from darts import concatenate
from StockDataSet import StockDataSet


class TimeSeriesPredict:
    host = 'localhost'
    user = 'root'
    password = "Mysql@2023"
    db = 'stock'
    port = 3306
    def __init__(self,*args):

        ticker = args[0]
        if len(ticker) > 0:
            self.stock_data_set = StockDataSet(ticker=ticker)
            self.validation = True
            self.train_val_ratio = 0.8
            self.model_type = ''
            self.model_name = ''
            self.past_covariates = []
            self.future_covariates = []
    def set_ticker(self,ticker):
        self.stock_data_set = StockDataSet(ticker=ticker)
        self.past_covariates = []
        self.future_covariates = []
    def preprocess_data(self):
        # norminalization
        scaler = self.target_series.get_scaler()
        series = self.target_series.get_series()
        target = scaler.fit_transform(series)
        # split
        target_len = len(target)
        train_len = int(target_len * self.train_val_ratio)
        self.train_target , self.val_target = target[:train_len],target[train_len:]
        self.target = target
        train_past_covariates = []
        val_past_covariates = []
        train_future_covariate=[]
        val_future_covariate = []
        past_covariates = []
        future_covariate = []
        for stock_series in self.past_covariates:
            scaler = stock_series.get_scaler()
            series = stock_series.get_series()
            target = scaler.fit_transform(series)
            # split
            target_len = len(target)
            train_len = int(target_len * self.train_val_ratio)
            train, val = target[:train_len], target[train_len:]
            train_past_covariates.append(train)
            val_past_covariates.append(val)
            past_covariates.append(target)

        for stock_series in self.future_covariates:
            scaler = stock_series.get_scaler()
            series = stock_series.get_series()
            target = scaler.fit_transform(series)
            # split
            target_len = len(target)
            train_len = int(target_len * self.train_val_ratio)
            train, val = target[:train_len], target[train_len:]
            train_future_covariate.append(train)
            val_future_covariate.append(val)
            future_covariate.append(target)
        if len(train_past_covariates) > 0:
            self.past_train_multi = concatenate(train_past_covariates, axis=1)
            self.past_val_multi = concatenate(val_past_covariates, axis=1)
            self.past_multi = concatenate(past_covariates, axis=1)
        if len(train_future_covariate) > 0:
            self.future_train_multi = concatenate(train_future_covariate, axis=1)
            self.future_val_multi = concatenate(val_future_covariate, axis=1)
            self.future_multi = concatenate(future_covariate, axis=1)
    def add_field(self,field_name,start_time,stop_time):
        self.stock_data_set.add_field(field_name,start_time,stop_time)

    def add_field_from_dataframe(self, field_name, df):
        """
        Add a field from a pre-calculated dataframe (e.g., technical indicators)

        Args:
            field_name: Name of the field/indicator
            df: DataFrame with 'date' and the field_name columns
        """
        self.stock_data_set.add_field_from_dataframe(field_name, df)

    def set_model_type(self,model_type):
        self.model_type = model_type
    def set_model_name(self,model_name):
        self.model_name = model_name

    def train(self, id):
        """
        Generic train implementation for all child classes.
        Handles directory creation and model saving automatically.

        Args:
            id: Solution/model ID for naming the saved file
        """
        # Create directory structure BEFORE training
        base_path = os.getcwd()
        # Use __class__.__name__ for compatibility with all model types (RandomForest doesn't have model_name)
        model_name = getattr(self.model, 'model_name', self.model.__class__.__name__)
        model_dir = os.path.join(base_path, model_name)
        os.makedirs(model_dir, exist_ok=True)

        # Set work directory for Darts internal logging (use base path, not model_name)
        # This prevents duplicate path structure: work_dir should be parent directory
        self.model.work_dir = base_path

        # CRITICAL FIX: Reset lags_past_covariates and lags_future_covariates to None
        # This handles both NEW models (initialized in __init__) and LOADED models
        # For loaded models, they may have old lags parameters saved that need to be reset
        if hasattr(self.model, 'lags_past_covariates'):
            self.model.lags_past_covariates = None
        if hasattr(self.model, 'lags_future_covariates'):
            self.model.lags_future_covariates = None
        print("[TRAIN] Reset model lags_past_covariates and lags_future_covariates to None")

        # Check model's covariate support using Darts internal properties
        # This prevents passing unsupported covariates that would cause ValueError
        supports_past = getattr(self.model, 'supports_past_covariates', True)
        supports_future = getattr(self.model, 'supports_future_covariates', True)

        # Prepare covariates based on model support AND actual data availability
        past_cov = self.past_train_multi if (hasattr(self, 'past_train_multi') and supports_past) else None
        future_cov = self.future_train_multi if (hasattr(self, 'future_train_multi') and supports_future) else None
        val_past_cov = self.past_val_multi if (hasattr(self, 'past_val_multi') and supports_past) else None
        val_future_cov = self.future_val_multi if (hasattr(self, 'future_val_multi') and supports_future) else None

        # CRITICAL FIX for sklearn-based models (CatBoost, XGBoost, LightGBM):
        # Dynamically set lags_past_covariates and lags_future_covariates based on actual data availability
        # This prevents "lags parameter set but no data provided" ValueError from Darts
        if hasattr(self, 'lags_past_covariates') and hasattr(self.model, 'lags_past_covariates'):
            if past_cov is not None and len(self.past_covariates) > 0:
                # We have past covariate data, set the lags parameter
                self.model.lags_past_covariates = self.lags_past_covariates
                print(f"[TRAIN] Setting model lags_past_covariates: {self.lags_past_covariates}")
            else:
                # No past covariate data, ensure lags is None
                self.model.lags_past_covariates = None
                print(f"[TRAIN] No past covariates data - setting lags_past_covariates=None")

        if hasattr(self, 'lags_future_covariates') and hasattr(self.model, 'lags_future_covariates'):
            if future_cov is not None and len(self.future_covariates) > 0:
                # We have future covariate data, set the lags parameter
                self.model.lags_future_covariates = self.lags_future_covariates
                print(f"[TRAIN] Setting model lags_future_covariates: {self.lags_future_covariates}")
            else:
                # No future covariate data, ensure lags is None
                self.model.lags_future_covariates = None
                print(f"[TRAIN] No future covariates data - setting lags_future_covariates=None")

        # Log covariate filtering if any were filtered out
        if hasattr(self, 'past_train_multi') and not supports_past:
            print(f"[TRAIN] Model {self.model.__class__.__name__} does not support past_covariates - filtering them out")
        if hasattr(self, 'future_train_multi') and not supports_future:
            print(f"[TRAIN] Model {self.model.__class__.__name__} does not support future_covariates - filtering them out")

        # Train the model with model-aware covariate handling
        self.model.fit(
            self.train_target,
            past_covariates=past_cov,
            future_covariates=future_cov,
            val_series=self.val_target if hasattr(self, 'val_target') else None,
            val_past_covariates=val_past_cov,
            val_future_covariates=val_future_cov,
            verbose=True
        )

        # Determine file extension based on model type
        file_extension = self._get_model_file_extension()
        model_filename = f"model_{id}{file_extension}"
        path = os.path.join(model_dir, model_filename)

        # Save model
        self.model.save(path)
        print(f"[TRAIN] Model saved successfully to: {path}")
        return path

    def _get_model_file_extension(self):
        """
        Determine the file extension based on model type.
        Torch models use .pt, sklearn-based models use .pkl

        Returns:
            str: File extension (.pt or .pkl)
        """
        # Check if it's a torch model
        if hasattr(self.model, '__class__'):
            model_class_name = self.model.__class__.__name__
            # Torch-based models
            if any(x in model_class_name for x in ['DLinear', 'NLinear', 'NHits', 'NBeats', 'TFT',
                                                     'TCN', 'Transformer', 'RNN', 'BlockRNN',
                                                     'TimeDeepEncoder']):
                return '.pt'
            # Sklearn-based models
            elif any(x in model_class_name for x in ['RandomForest', 'CatBoost', 'LightGBM', 'XGBoost']):
                return '.pkl'
        # Default to .pt for torch models
        return '.pt'
    def predict(self,start_date,predict_length):
        start_date = pd.to_datetime(start_date,format='%Y-%m-%d')
        scaler = self.target_series.get_scaler()
        series = self.target_series.get_series()
        start_index = series.get_index_at_point(start_date)

        # For sklearn models, we need to include historical data for lag lookback
        # The model needs data BEFORE start_date to make predictions
        # Include data from the beginning of the loaded series up to start_date
        # This ensures models have enough historical context
        history_start = 0  # Start from beginning of loaded series (which should include historical data)
        end_index = start_index + int(predict_length)

        # Get series including historical data for lag lookback
        series = series[history_start:end_index]
        self.predict_target = scaler.fit_transform(series)
        past_covariates = []
        for stock_series in self.past_covariates:
            scaler = stock_series.get_scaler()
            series = stock_series.get_series()
            past_corvariate = scaler.fit_transform(series)
            past_covariates.append(past_corvariate)
        if len(past_covariates) > 0:
            self.predict_past_covariates = concatenate(past_covariates,axis=1)
        future_covariates = []
        for stock_series in self.future_covariates:
            scaler = stock_series.get_scaler()
            series = stock_series.get_series()
            future_covariate = scaler.fit_transform(series)
            future_covariate = future_covariate[:end_index+int(predict_length)+1]
            future_covariates.append(future_covariate)
        if len(future_covariates) > 0:
            self.predict_future_covariates = concatenate(future_covariates,axis=1)
    def getModelType(self):
        pass
    def getModelConfigurationParam(self):
        pass
    def add_past_covariate(self,field_name):
        past_series = self.stock_data_set.get_stock_time_series(field_name=field_name)
        self.past_covariates.append(past_series)
    def add_future_covariate(self,field_name):
        future_series = self.stock_data_set.get_stock_time_series(field_name=field_name)
        self.future_covariates.append(future_series)
    def set_target_series(self,field_name):
        self.target_series = self.stock_data_set.get_stock_time_series(field_name=field_name)
    def evaluate_model(self):
        pass

    def get_model_specific_params(self):
        """
        Hook method for child classes to provide model-specific parameters.
        Override this in child classes to return a dict of model-specific params.

        Returns:
            dict: Model-specific parameters to save
        """
        return {}

    def set_model_specific_params(self, model):
        """
        Hook method for child classes to restore model-specific parameters.
        Override this in child classes to restore model-specific instance variables.

        Args:
            model: Loaded model instance
        """
        pass

    def get_model_class(self):
        """
        Hook method for child classes to provide the model class for loading.
        Override this in child classes to return the appropriate model class.

        Returns:
            class: The Darts model class (e.g., DLinearModel, NLinearModel)
        """
        raise NotImplementedError("Child classes must implement get_model_class()")

    def save_model(self, file_name, user_model_name):
        """
        Generic save_model implementation for all child classes.
        Uses template method pattern to handle model-specific parameters.

        Args:
            file_name: Name of the file to save (e.g., "model_31.pt")
            user_model_name: Directory name for the model (e.g., "dlinear_model_001")
        """
        # Create directory structure
        base_path = os.getcwd()
        model_dir = os.path.join(base_path, user_model_name)
        os.makedirs(model_dir, exist_ok=True)

        # Build full file path
        full_path = os.path.join(model_dir, file_name)

        # Update model name (some models like RandomForest don't have model_name attribute)
        if hasattr(self.model, 'model_name'):
            self.model.model_name = user_model_name

        # Update common model parameters
        if hasattr(self, 'input_chunk_length'):
            self.model.model_params['input_chunk_length'] = self.input_chunk_length
        if hasattr(self, 'output_chunk_length'):
            self.model.model_params['output_chunk_length'] = self.output_chunk_length
        if hasattr(self, 'batch_size'):
            self.model.model_params['batch_size'] = self.batch_size
        if hasattr(self, 'n_epochs'):
            self.model.model_params['n_epochs'] = self.n_epochs
            self.model.n_epochs = self.n_epochs

        # Update model-specific parameters (delegated to child class)
        model_specific_params = self.get_model_specific_params()
        for param_name, param_value in model_specific_params.items():
            self.model.model_params[param_name] = param_value

        # Save model
        self.model.save(full_path)
        print(f"[SAVE_MODEL] Model saved to: {full_path}")
        return full_path

    def load_model(self, path):
        """
        Generic load_model implementation for all child classes.
        Uses template method pattern to handle model-specific parameters.

        Args:
            path: Full path to the model file or just the filename
        """
        # Get the model class from child
        model_class = self.get_model_class()

        # Load the model
        model = model_class.load(path=path)

        # Restore common parameters
        if hasattr(model, 'input_chunk_length'):
            self.input_chunk_length = model.input_chunk_length
        if hasattr(model, 'output_chunk_length'):
            self.output_chunk_length = model.output_chunk_length
        if hasattr(model, 'model_params'):
            if 'batch_size' in model.model_params:
                self.batch_size = model.model_params.get('batch_size')
            if 'n_epochs' in model.model_params:
                self.n_epochs = model.model_params.get('n_epochs')

        # Restore model-specific parameters (delegated to child class)
        self.set_model_specific_params(model)

        # Set the loaded model
        self.model = model
        print(f"[LOAD_MODEL] Model loaded from: {path}")
        return model

    def set_working_dir(self,working_dir):
        self.working_dir = working_dir
    def get_working_dir(self):
        return self.working_dir
    def get_latest_training_date(self):
        pass
    def set_validation(self,validation):
        self.validation = validation
        if validation == False:
            self.train_val_ratio = 1
        else:
            self.train_val_ratio = 0.8
    def set_train_ratio(self,train_ratio):
        if self.validation == True:
            self.train_val_ratio = train_ratio
    def get_chunk_length(self):
        pass

    def get_max_prediction_length(self):
        """
        Returns the maximum prediction length the model can produce in a single call.

        For torch encoder-decoder models (NBeats, NHits, TFT, etc.): Limited by output_chunk_length
        For sklearn models (XGBoost, CatBoost, etc.): Can predict any length via auto-regression
        For RNN models: Can predict any length (no hard limit)

        Returns:
            int: Maximum prediction length for this model type
        """
        # Check if this is an sklearn-based model (XGBoost, CatBoost, LightGBM, RandomForest)
        # These models have output_chunk_length=1 but can predict any length via iteration
        model_class_name = self.model.__class__.__name__ if hasattr(self, 'model') else ''
        sklearn_models = ['XGBModel', 'CatBoostModel', 'LightGBMModel', 'RandomForest']

        if any(sklearn_name in model_class_name for sklearn_name in sklearn_models):
            # Sklearn models can predict any length - return a reasonable max
            return 365  # Allow up to 1 year

        # Check if this is an RNN model (no output_chunk_length)
        if not hasattr(self, 'output_chunk_length'):
            return 365  # Allow up to 1 year for flexible models

        # For encoder-decoder models, return their output_chunk_length
        return self.output_chunk_length
















