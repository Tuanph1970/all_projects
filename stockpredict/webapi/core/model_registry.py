"""
Model Registry - Factory Pattern Implementation
Centralized management for all prediction model types
"""
from typing import Tuple, Type, Dict, List, Optional
from Models.RNNPredictModel import RNNPredictModel
from Models.BlockRNNPredictModel import BlockRNNPredictModel
from Models.NBeatsPredictModel import NBeatsPredictModel
from Models.NHitsPredictModel import NHitsPredictModel
from Models.TCNPredictModel import TCNPredictModel
from Models.TransformerPredictModel import TransformerPredictModel
from Models.TFTPredictModel import TFTPredictModel
from Models.DLinearPredictModel import DLinearPredictModel
from Models.NLinearPredictModel import NLinearPredictModel
from Models.TimeDeepEncoderPredictModel import TimeDeepEncoderPredictModel
from Models.RandomForestPredictModel import RandomForestPredictModel
from Models.LightGBMPredictModel import LightGBMPredictModel
from Models.XGBoostPredictModel import XGBootsPredictModel
from Models.CatBoostPredictModel import CatBoostPredictModel


class ModelRegistry:
    """
    Centralized registry for all prediction model types.
    Implements Factory Pattern to eliminate code duplication.
    """

    # Model registry: model_type -> (ModelClass, file_extension)
    _MODEL_REGISTRY: Dict[str, Tuple[Type, str]] = {
        'BlockRNN': (BlockRNNPredictModel, '.pt'),
        'RNN': (RNNPredictModel, '.pt'),
        'NBeats': (NBeatsPredictModel, '.pt'),
        'NHits': (NHitsPredictModel, '.pt'),
        'TCN': (TCNPredictModel, '.pt'),
        'Transformer': (TransformerPredictModel, '.pt'),
        'TFT': (TFTPredictModel, '.pt'),
        'DLinear': (DLinearPredictModel, '.pt'),
        'NLinear': (NLinearPredictModel, '.pt'),
        'TiDE': (TimeDeepEncoderPredictModel, '.pt'),
        'RandomForest': (RandomForestPredictModel, '.pkl'),
        'LightGBM': (LightGBMPredictModel, '.pkl'),
        'XGBoost': (XGBootsPredictModel, '.pkl'),
        'CatBoost': (CatBoostPredictModel, '.pkl'),
    }

    # Tree-based ML models use lag-based parameters instead of chunk-based
    # This list helps filter incompatible parameters from neural network model configs
    _TREE_BASED_MODELS = {'RandomForest', 'LightGBM', 'XGBoost', 'CatBoost'}

    # Parameter mappings between neural network and tree-based models
    # Neural network models use 'input_chunk_length', tree-based use 'lag_len'
    _NEURAL_NETWORK_ONLY_PARAMS = {
        # Core neural network parameters
        'input_chunk_length', 'hidden_dim', 'n_rnn_layers', 'num_stacks',
        'num_blocks', 'num_layers', 'layer_widths', 'expansion_coefficient_dim',
        'd_model', 'nhead', 'num_encoder_layers', 'num_decoder_layers',
        'dim_feedforward', 'kernel_size', 'num_filters', 'dilation_base',
        'weight_norm', 'hidden_size', 'lstm_layers', 'num_attention_heads',
        'full_attention', 'feed_forward', 'hidden_continuous_size',
        'decoder_output_dim', 'temporal_width_past', 'temporal_width_future',
        'temporal_decoder_hidden', 'use_layer_norm', 'dropout', 'shared_weights',
        'const_init', 'normalize', 'use_reversible_instance_norm',
        # Training-specific parameters (neural networks only)
        'batch_size', 'n_epochs', 'learning_rate', 'optimizer_kwargs',
        'lr_scheduler_cls', 'lr_scheduler_kwargs', 'loss_fn',
        'torch_metrics', 'pl_trainer_kwargs', 'force_reset', 'save_checkpoints',
    }

    _TREE_BASED_ONLY_PARAMS = {
        'lag_len', 'lag_past_len', 'lag_future_len', 'n_estimators',
        'max_depth', 'categorical_past_covariates', 'categorical_future_covariates',
    }

    @classmethod
    def get_model_class(cls, model_type: str) -> Tuple[Type, str]:
        """
        Get model class and file extension for a given model type.

        Args:
            model_type: Type of model (e.g., 'BlockRNN', 'NBeats')

        Returns:
            Tuple of (ModelClass, file_extension)

        Raises:
            ValueError: If model_type is not registered
        """
        if model_type not in cls._MODEL_REGISTRY:
            raise ValueError(
                f"Unknown model type: {model_type}. "
                f"Supported types: {', '.join(cls.get_supported_model_types())}"
            )

        return cls._MODEL_REGISTRY[model_type]

    @classmethod
    def create_model_instance(cls, model_type: str):
        """
        Create a new instance of the specified model type.

        Args:
            model_type: Type of model to instantiate

        Returns:
            New instance of the model class
        """
        model_class, _ = cls.get_model_class(model_type)
        return model_class()

    @classmethod
    def get_file_extension(cls, model_type: str) -> str:
        """
        Get the file extension for a given model type.

        Args:
            model_type: Type of model

        Returns:
            File extension (e.g., '.pt', '.pkl')
        """
        _, extension = cls.get_model_class(model_type)
        return extension

    @classmethod
    def get_supported_model_types(cls) -> List[str]:
        """
        Get list of all supported model types.

        Returns:
            List of model type names
        """
        return list(cls._MODEL_REGISTRY.keys())

    @classmethod
    def is_model_type_supported(cls, model_type: str) -> bool:
        """
        Check if a model type is supported.

        Args:
            model_type: Type of model to check

        Returns:
            True if supported, False otherwise
        """
        return model_type in cls._MODEL_REGISTRY

    @classmethod
    def get_pytorch_models(cls) -> List[str]:
        """
        Get list of PyTorch-based models (.pt extension).

        Returns:
            List of PyTorch model names
        """
        return [
            model_type for model_type, (_, ext) in cls._MODEL_REGISTRY.items()
            if ext == '.pt'
        ]

    @classmethod
    def get_sklearn_models(cls) -> List[str]:
        """
        Get list of scikit-learn based models (.pkl extension).

        Returns:
            List of sklearn model names
        """
        return [
            model_type for model_type, (_, ext) in cls._MODEL_REGISTRY.items()
            if ext == '.pkl'
        ]

    @classmethod
    def register_model(cls, model_type: str, model_class: Type, file_extension: str):
        """
        Register a new model type (for extensibility).

        Args:
            model_type: Name of the model type
            model_class: Model class
            file_extension: File extension for saved models
        """
        if model_type in cls._MODEL_REGISTRY:
            raise ValueError(f"Model type '{model_type}' is already registered")

        if file_extension not in ['.pt', '.pkl']:
            raise ValueError(f"Unsupported file extension: {file_extension}")

        cls._MODEL_REGISTRY[model_type] = (model_class, file_extension)

    @classmethod
    def is_tree_based_model(cls, model_type: str) -> bool:
        """
        Check if a model type is a tree-based ML model.

        Args:
            model_type: Type of model to check

        Returns:
            True if tree-based (LightGBM, XGBoost, etc.), False otherwise
        """
        return model_type in cls._TREE_BASED_MODELS

    @classmethod
    def filter_config_for_model_type(cls, model_type: str, config: Dict) -> Dict:
        """
        Filter configuration parameters to only include those valid for the specified model type.
        This prevents parameter mismatch errors when creating models.

        Each model type (BlockRNN, NBeats, TCN, LightGBM, etc.) has its own unique set of
        parameters. This method uses introspection to dynamically determine valid parameters
        by examining the model's setModelConfigurationParam method signature.

        Args:
            model_type: Type of model to create
            config: Full configuration dictionary (may contain mixed parameters)

        Returns:
            Filtered configuration with only valid parameters for the model type
        """
        if not config:
            return {}

        # Use introspection to get the exact valid parameters for this model type
        # This is the most reliable method as each model has unique parameter signatures
        valid_params = cls.get_valid_params_for_model(model_type)

        if valid_params:
            # Filter to only include parameters that the model actually accepts
            filtered_config = {k: v for k, v in config.items() if k in valid_params}
            return filtered_config

        # Fallback: If introspection fails, use category-based filtering
        filtered_config = {}
        is_tree_based = cls.is_tree_based_model(model_type)

        for key, value in config.items():
            # Skip parameters that are only for the other model category
            if is_tree_based and key in cls._NEURAL_NETWORK_ONLY_PARAMS:
                continue
            if not is_tree_based and key in cls._TREE_BASED_ONLY_PARAMS:
                continue
            filtered_config[key] = value

        return filtered_config

    # Cache for model parameter signatures to avoid repeated introspection
    _PARAM_CACHE: Dict[str, set] = {}

    @classmethod
    def get_valid_params_for_model(cls, model_type: str) -> set:
        """
        Get valid configuration parameter names for a model type by introspecting
        the model's setModelConfigurationParam method signature.

        Results are cached to avoid repeated model instantiation.

        Args:
            model_type: Type of model

        Returns:
            Set of valid parameter names
        """
        # Check cache first
        if model_type in cls._PARAM_CACHE:
            return cls._PARAM_CACHE[model_type]

        import inspect
        try:
            model_class, _ = cls.get_model_class(model_type)
            model_instance = model_class()
            if hasattr(model_instance, 'setModelConfigurationParam'):
                sig = inspect.signature(model_instance.setModelConfigurationParam)
                valid_params = set(sig.parameters.keys())
                # Cache the result
                cls._PARAM_CACHE[model_type] = valid_params
                return valid_params
        except Exception as e:
            print(f"[ModelRegistry] Warning: Could not introspect {model_type}: {e}")
        return set()
