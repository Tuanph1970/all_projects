"""
Model Service - Enhanced with UnifiedModelService integration
This version integrates the new unified architecture for better model management
"""
from typing import Dict, List, Optional
from repositories.model_repository import ModelRepository, ModelParameterRepository
from repositories.all_models_repository import AllModelsRepository
from repositories.model_capability_repository import ModelCapabilityRepository
from core.factories import PredictModelFactory
from core.exceptions import ModelCreationException, EntityNotFoundException
from core.observers import ModelEventPublisher
from core.unified_model_service import UnifiedModelService
from core.model_registry import ModelRegistry


class ModelService:
    """
    Enhanced Model Service integrating UnifiedModelService.
    Provides backward compatibility while leveraging new architecture.
    """

    def __init__(self):
        # Legacy repositories (keep for backward compatibility)
        self.model_repo = ModelRepository()
        self.param_repo = ModelParameterRepository()
        self.all_models_repo = AllModelsRepository()
        self.capability_repo = ModelCapabilityRepository()
        self.event_publisher = ModelEventPublisher()

        # New unified service
        self.unified_service = UnifiedModelService()

    def create_model(self, model_name: str, model_type: str, model_sub_type: str = None,
                    past_covariate: bool = None, future_covariate: bool = None,
                    parameters: Dict = None, created_by: str = None,
                    user_id: str = None) -> Dict:
        """
        Create a new model using the new unified architecture.
        Covariate capabilities are automatically loaded from database if not explicitly provided.

        Args:
            model_name: Name of the model
            model_type: Type of model (BlockRNN, NBeats, etc.)
            model_sub_type: Sub-type (LSTM, GRU, etc.)
            past_covariate: Whether model uses past covariates (None=auto-detect from DB)
            future_covariate: Whether model uses future covariates (None=auto-detect from DB)
            parameters: Model configuration parameters
            created_by: User who created the model
            user_id: Owner of the model (defaults to created_by)

        Returns:
            Dictionary with model information
        """
        try:
            # Use user_id or fall back to created_by
            owner_id = user_id or created_by or 'default_user'

            # Validate model type
            if not ModelRegistry.is_model_type_supported(model_type):
                raise ModelCreationException(
                    model_type,
                    f"Unsupported model type. Supported types: {', '.join(ModelRegistry.get_supported_model_types())}"
                )

            # Auto-detect covariate capabilities from database if not explicitly provided
            if past_covariate is None or future_covariate is None:
                try:
                    capabilities = self.capability_repo.get_capabilities_by_model_type(model_type)
                    if past_covariate is None:
                        past_covariate = capabilities['supports_past_covariates']
                    if future_covariate is None:
                        future_covariate = capabilities['supports_future_covariates']
                except EntityNotFoundException:
                    # If model type not found in capabilities table, default to False
                    if past_covariate is None:
                        past_covariate = False
                    if future_covariate is None:
                        future_covariate = False

            # Create model using unified service
            result = self.unified_service.create_model(
                model_type=model_type,
                model_sub_type=model_sub_type,
                model_name=model_name,
                user_id=owner_id,
                config=parameters or {},
                past_covariate=past_covariate,
                future_covariate=future_covariate,
                created_by=created_by or owner_id
            )

            model_id = result['model_id']

            # Publish event
            self.event_publisher.model_created(model_id, model_type, model_name)

            return {
                'model_id': model_id,
                'model_name': model_name,
                'model_type': model_type,
                'model_sub_type': model_sub_type,
                'past_covariate': past_covariate,
                'future_covariate': future_covariate,
                'status': 'created',
                'file_path': result.get('file_path'),
                'configuration': result.get('configuration')
            }

        except Exception as e:
            raise ModelCreationException(model_type, str(e))

    def get_model_by_id(self, model_id: int) -> Dict:
        """
        Get model information by ID.

        Args:
            model_id: Model instance ID

        Returns:
            Model information with parameters
        """
        try:
            # Get model instance from unified service
            model_info = self.unified_service.instance_repo.get_model_instance(model_id)

            # Get parameters
            parameters = self.unified_service.get_model_parameters_by_id(model_id)

            return {
                'model_id': model_info['id'],
                'model_name': model_info['model_name'],
                'model_type': model_info['model_type'],
                'model_sub_type': model_info['model_sub_type'],
                'user_id': model_info['user_id'],
                'status': model_info['status'],
                'file_path': model_info['file_path'],
                'last_training_date': model_info['last_training_date'],
                'created_at': model_info['created_at'],
                'updated_at': model_info['updated_at'],
                'parameters': parameters
            }

        except Exception as e:
            raise EntityNotFoundException("Model", model_id)

    def get_all_models(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        Get all models, optionally filtered by user.

        Args:
            user_id: Optional user filter

        Returns:
            List of model information
        """
        if user_id:
            return self.unified_service.get_user_models(user_id)
        else:
            # Get all active models
            return self.unified_service.instance_repo.execute_query(
                "SELECT * FROM model_instances WHERE status != 'archived' ORDER BY created_at DESC"
            )

    def update_model(self, model_id: int, model_name: str = None, model_type: str = None,
                    model_sub_type: str = None, parameters: Dict = None) -> bool:
        """
        Update model configuration.

        Args:
            model_id: Model instance ID
            model_name: New model name (optional)
            model_type: New model type (optional, not recommended)
            model_sub_type: New sub-type (optional)
            parameters: Updated parameters (optional)

        Returns:
            True if updated successfully
        """
        updates = {}

        if model_name:
            updates['model_name'] = model_name
        if model_sub_type:
            updates['model_sub_type'] = model_sub_type
        if parameters:
            updates['config_json'] = parameters

        success = self.unified_service.instance_repo.update_model_instance(model_id, **updates)

        # If parameters were updated, also save the model
        if parameters and success:
            self.unified_service.save_model(model_id, parameters)

        return success

    def delete_model(self, model_id: int, hard_delete: bool = False) -> bool:
        """
        Delete a model.

        Args:
            model_id: Model instance ID
            hard_delete: If True, permanently delete

        Returns:
            True if deleted successfully
        """
        success = self.unified_service.delete_model(model_id, hard_delete)

        if success:
            self.event_publisher.model_deleted(model_id)

        return success

    def get_models_by_type(self, model_type: str, user_id: Optional[str] = None) -> List[Dict]:
        """
        Get models by type.

        Args:
            model_type: Model type to filter
            user_id: Optional user filter

        Returns:
            List of models
        """
        return self.unified_service.instance_repo.get_models_by_type(model_type, user_id)

    def get_models_by_user(self, user_id: str, status: Optional[str] = None) -> List[Dict]:
        """
        Get all models created by a specific user.

        Args:
            user_id: User identifier
            status: Optional status filter

        Returns:
            List of user's models
        """
        return self.unified_service.get_user_models(user_id, status)

    def get_supported_model_types(self) -> List[str]:
        """
        Get list of supported model types.

        Returns:
            List of model type names
        """
        return ModelRegistry.get_supported_model_types()

    def get_all_model_types(self, active_only: bool = True) -> List[Dict]:
        """
        Get all available model types with their sub-models from database.

        Args:
            active_only: If True, only return active model types

        Returns:
            List of model types with sub-models
        """
        return self.all_models_repo.get_all_models_with_subtypes(active_only=active_only)

    def get_model_parameters_detail(self, model_type: str) -> Dict:
        """
        Get detailed parameter information for a model type.

        Args:
            model_type: Model type

        Returns:
            Parameter details
        """
        from Models.Common import getModelParameterDetail
        return getModelParameterDetail(model_type)

    def load_model_for_prediction(self, model_id: int):
        """
        Load a model for prediction (new method using unified service).

        Args:
            model_id: Model instance ID

        Returns:
            Loaded model instance ready for prediction
        """
        return self.unified_service.load_model(model_id)

    def update_training_status(self, model_id: int, status: str,
                               metrics: Optional[Dict] = None,
                               create_version: bool = True) -> bool:
        """
        Update model training status.

        Args:
            model_id: Model instance ID
            status: New status (training, trained, failed)
            metrics: Training metrics
            create_version: Whether to create version snapshot

        Returns:
            True if updated successfully
        """
        return self.unified_service.update_training_status(
            model_id, status, metrics, create_version
        )

    def get_model_versions(self, model_id: int) -> List[Dict]:
        """
        Get all versions for a model.

        Args:
            model_id: Model instance ID

        Returns:
            List of model versions
        """
        return self.unified_service.get_model_versions(model_id)

    def load_model_version(self, model_id: int, version: int):
        """
        Load a specific version of a model.

        Args:
            model_id: Model instance ID
            version: Version number

        Returns:
            Loaded model instance
        """
        return self.unified_service.load_model_version(model_id, version)

    def search_models(self, search_term: str, user_id: Optional[str] = None) -> List[Dict]:
        """
        Search models by name.

        Args:
            search_term: Search term
            user_id: Optional user filter

        Returns:
            List of matching models
        """
        return self.unified_service.instance_repo.search_models(search_term, user_id)

    def get_user_storage_info(self, user_id: str) -> Dict:
        """
        Get storage information for a user.

        Args:
            user_id: User identifier

        Returns:
            Storage statistics
        """
        models = self.get_models_by_user(user_id)
        total_size = self.unified_service.storage_manager.get_directory_size(user_id)
        model_files = self.unified_service.storage_manager.get_user_models_list(user_id)

        return {
            'user_id': user_id,
            'total_models': len(models),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'model_files': len(model_files),
            'storage_path': self.unified_service.storage_manager.get_user_directory(user_id)
        }

    def get_model_by_id_with_file(self, model_id: int, model_name: str, model_type: str):
        """
        Load model from file (legacy method for backward compatibility).

        Args:
            model_id: Model instance ID
            model_name: Model name (not used in new architecture)
            model_type: Model type (not used in new architecture)

        Returns:
            Loaded model instance
        """
        # Use new unified service to load model
        return self.unified_service.load_model(model_id)

    def get_model_default_parameters(self) -> List[Dict]:
        """
        Get default model parameter values from database.

        Returns:
            List of default parameter values
        """
        query = "SELECT * FROM tbl_model_defaul_value"
        return self.model_repo.execute_query(query)

    def get_model_parameter_fields(self) -> List[Dict]:
        """
        Get model parameter field definitions from database.

        Returns:
            List of parameter field definitions
        """
        query = "SELECT * FROM tbl_model_field"
        return self.model_repo.execute_query(query)

    def get_options_by_parameter(self) -> List[Dict]:
        """
        Get available options for each parameter from database.

        Returns:
            List of parameter options
        """
        query = """
        SELECT param_name, GROUP_CONCAT(option_value) as options
        FROM tbl_param_option
        GROUP BY param_name
        """
        return self.model_repo.execute_query(query)

    def get_model_capabilities(self, model_type: str) -> Dict:
        """
        Get covariate capabilities for a specific model type.

        Args:
            model_type: Type of model (DLinear, RNN, etc.)

        Returns:
            Dictionary with capability information
        """
        return self.capability_repo.get_capabilities_by_model_type(model_type)

    def get_all_model_capabilities(self, active_only: bool = True) -> List[Dict]:
        """
        Get all model capabilities.

        Args:
            active_only: If True, only return active model types

        Returns:
            List of capability dictionaries
        """
        return self.capability_repo.get_all_capabilities(active_only)

    def check_model_covariate_support(self, model_type: str, covariate_type: str) -> bool:
        """
        Check if a model type supports a specific covariate type.

        Args:
            model_type: Type of model
            covariate_type: 'past', 'future', or 'both'

        Returns:
            True if the model supports the covariate type
        """
        return self.capability_repo.check_covariate_support(model_type, covariate_type)
