"""
Unified Model Service - Replaces all 30+ create/save functions in Common.py
Centralized service for all model operations
"""
import os
import json
from typing import Dict, Optional, List
from core.model_registry import ModelRegistry
from core.model_storage_manager import ModelStorageManager
from repositories.model_instance_repository import ModelInstanceRepository
from repositories.model_version_repository import ModelVersionRepository
from core.exceptions import ModelCreationException, EntityNotFoundException


class UnifiedModelService:
    """
    Unified service for all model operations.
    Replaces the scattered functions in Common.py with a clean, centralized API.
    """

    # Fields that should NOT be passed to setModelConfigurationParam
    # These are database/metadata fields, not model configuration parameters
    EXCLUDED_CONFIG_FIELDS = {
        'id', 'model_id', 'model_name', 'model_type',
        'created_at', 'updated_at', 'created_by', 'user_id',
        'file_path', 'status', 'last_training_date',
        'past_covariate', 'future_covariate', 'config_json',
        'file_extension'
    }

    def __init__(self, storage_manager: Optional[ModelStorageManager] = None):
        """
        Initialize unified model service.

        Args:
            storage_manager: Optional custom storage manager
        """
        self.storage_manager = storage_manager or ModelStorageManager()
        self.instance_repo = ModelInstanceRepository()
        self.version_repo = ModelVersionRepository()

    def create_model(self, model_type: str, model_sub_type: Optional[str],
                    model_name: str, user_id: str, config: Dict,
                    past_covariate: bool = False, future_covariate: bool = False,
                    created_by: Optional[str] = None) -> Dict:
        """
        Create a new model instance (replaces all create_*_model functions).

        Args:
            model_type: Type of model (BlockRNN, NBeats, etc.)
            model_sub_type: Sub-type (LSTM, GRU, etc.)
            model_name: User-defined model name
            user_id: Owner of the model
            config: Configuration parameters as dictionary
            past_covariate: Whether model uses past covariates
            future_covariate: Whether model uses future covariates
            created_by: User who created the model

        Returns:
            Dictionary with model instance information

        Raises:
            ModelCreationException: If creation fails
        """
        try:
            # Validate model type
            if not ModelRegistry.is_model_type_supported(model_type):
                raise ValueError(f"Unsupported model type: {model_type}")

            # Get file extension for this model type
            file_extension = ModelRegistry.get_file_extension(model_type)

            # Create database record
            model_id = self.instance_repo.create_model_instance(
                model_type=model_type,
                model_sub_type=model_sub_type,
                model_name=model_name,
                user_id=user_id,
                config_json=config,
                file_extension=file_extension,
                past_covariate=past_covariate,
                future_covariate=future_covariate,
                created_by=created_by
            )

            # Change working directory to user's folder BEFORE creating model instance
            # This ensures model captures correct working directory during initialization
            import os
            user_dir = self.storage_manager.get_user_directory(user_id)
            old_cwd = os.getcwd()

            try:
                os.chdir(user_dir)

                # Create model instance and set configuration AFTER changing directory
                # This way model's __init__ will use the user directory as base
                model = ModelRegistry.create_model_instance(model_type)

                # Filter config to only include valid model parameters
                # First, remove excluded fields (metadata, etc.)
                clean_config = {k: v for k, v in config.items()
                               if k not in self.EXCLUDED_CONFIG_FIELDS}
                # Then, filter parameters based on model type (neural network vs tree-based)
                # This prevents passing invalid parameters like 'input_chunk_length' to tree-based models
                clean_config = ModelRegistry.filter_config_for_model_type(model_type, clean_config)
                model.setModelConfigurationParam(**clean_config)

                # Save model file using correct path template:
                # users_model/{user_id}/{model_name}/model_{model_id}.ext
                filename = f"model_{model_id}{file_extension}"
                model.save_model(filename, model_name)

                # Store the relative path from users_model base
                # Correct template: user_id/model_name/filename (no double nesting)
                relative_path = os.path.join(
                    str(user_id),
                    model_name,
                    filename
                )

                self.instance_repo.update_model_instance(
                    model_id,
                    file_path=relative_path
                )
            finally:
                # Always restore working directory
                os.chdir(old_cwd)

            return {
                'model_id': model_id,
                'model_name': model_name,
                'model_type': model_type,
                'model_sub_type': model_sub_type,
                'status': 'created',
                'file_path': relative_path,
                'configuration': model.getModelConfigurationParam()
            }

        except Exception as e:
            raise ModelCreationException(model_type, str(e))

    def load_model(self, model_id: int):
        """
        Load a model from database configuration (init from DB, then load weights).

        Args:
            model_id: Model instance ID

        Returns:
            Loaded model instance

        Raises:
            EntityNotFoundException: If model not found
        """
        # Get model instance from database
        instance = self.instance_repo.get_model_instance(model_id)

        # Create model from registry
        model = ModelRegistry.create_model_instance(instance['model_type'])

        # Set configuration from database (with defensive filtering)
        clean_config = {k: v for k, v in instance['config_json'].items()
                       if k not in self.EXCLUDED_CONFIG_FIELDS}
        # Filter parameters based on model type (neural network vs tree-based)
        clean_config = ModelRegistry.filter_config_for_model_type(instance['model_type'], clean_config)
        model.setModelConfigurationParam(**clean_config)

        # Load trained weights if available
        # Check both status == 'trained' and if file exists (for backward compatibility)
        if instance['file_path']:
            # Handle both absolute and relative paths
            # Absolute paths start with '/' or contain drive letter on Windows
            file_path = instance['file_path']
            if os.path.isabs(file_path):
                absolute_path = file_path
            else:
                absolute_path = self.storage_manager.get_absolute_from_relative(file_path)

            if self.storage_manager.file_exists(absolute_path):
                try:
                    model.load_model(absolute_path)
                    print(f"[MODEL LOAD] Successfully loaded model weights from {absolute_path}")

                    # CRITICAL: Re-apply database configuration after loading weights
                    # Loading weights may restore old configuration from the saved file
                    # Database configuration should always take precedence
                    model.setModelConfigurationParam(**clean_config)
                    print(f"[MODEL LOAD] Applied database configuration: {clean_config}")
                except Exception as e:
                    print(f"[MODEL LOAD] WARNING: Failed to load model weights: {str(e)}")
                    # If status is 'trained' but loading fails, this is an error
                    if instance['status'] == 'trained':
                        raise
                    # Otherwise, it might be a newly created model, so continue
            else:
                print(f"[MODEL LOAD] WARNING: Model file not found at {absolute_path}")
                if instance['status'] == 'trained':
                    raise FileNotFoundError(f"Model file not found at {absolute_path}")

        return model

    def save_model(self, model_id: int, config: Dict) -> Dict:
        """
        Update model configuration and save (replaces all save_*_model functions).

        Args:
            model_id: Model instance ID
            config: Updated configuration parameters

        Returns:
            Updated model configuration
        """
        # Get existing model instance
        instance = self.instance_repo.get_model_instance(model_id)

        # Create model and update configuration
        model = ModelRegistry.create_model_instance(instance['model_type'])

        # Filter out non-configuration fields (id, model_id, model_name, etc.)
        # that should not be passed to setModelConfigurationParam
        # Note: model_sub_type IS a valid config param for some models (e.g., RNN: LSTM/GRU)
        model_config = {k: v for k, v in config.items()
                       if k not in self.EXCLUDED_CONFIG_FIELDS}
        # Filter parameters based on model type (neural network vs tree-based)
        model_config = ModelRegistry.filter_config_for_model_type(instance['model_type'], model_config)

        model.setModelConfigurationParam(**model_config)

        # Change working directory to user's folder (same approach as create_model)
        import os
        user_dir = self.storage_manager.get_user_directory(instance['user_id'])
        old_cwd = os.getcwd()

        try:
            os.chdir(user_dir)

            # Extract just the filename from the stored path
            # Path format: user_id/model_name/filename (corrected from double nesting)
            filename = os.path.basename(instance['file_path'])

            # Save model file (save_model creates its own subdirectories)
            model.save_model(filename, instance['model_name'])
        finally:
            # Always restore working directory
            os.chdir(old_cwd)

        # Update database with the filtered model configuration
        self.instance_repo.update_model_instance(
            model_id,
            config_json=model_config
        )

        return model.getModelConfigurationParam()

    def get_model_parameters_by_id(self, model_id: int) -> Dict:
        """
        Get model parameters by ID (replaces get_model_parameters_by_id).

        Args:
            model_id: Model instance ID

        Returns:
            Model configuration parameters with last training date
        """
        instance = self.instance_repo.get_model_instance(model_id)

        # Create model instance and set configuration from database
        model = ModelRegistry.create_model_instance(instance['model_type'])

        # Safely filter config_json before setting parameters
        clean_config = {k: v for k, v in instance['config_json'].items()
                       if k not in self.EXCLUDED_CONFIG_FIELDS}
        # Filter parameters based on model type (neural network vs tree-based)
        clean_config = ModelRegistry.filter_config_for_model_type(instance['model_type'], clean_config)

        model.setModelConfigurationParam(**clean_config)
        config = model.getModelConfigurationParam()

        # Add last training date from database
        config['last_training_date'] = instance.get('last_training_date')

        return config

    def get_model_parameters(self, model_type: str) -> Dict:
        """
        Get default parameters for a model type (replaces get_model_parameters).

        Args:
            model_type: Type of model

        Returns:
            Default configuration parameters
        """
        model = ModelRegistry.create_model_instance(model_type)
        return model.getModelConfigurationParam()

    def update_training_status(self, model_id: int, status: str,
                               metrics: Optional[Dict] = None,
                               create_version: bool = True) -> bool:
        """
        Update model training status and optionally create a version snapshot.

        Args:
            model_id: Model instance ID
            status: New status (training, trained, failed)
            metrics: Training metrics
            create_version: Whether to create a version snapshot

        Returns:
            True if updated successfully
        """
        instance = self.instance_repo.get_model_instance(model_id)

        # Update main instance status
        success = self.instance_repo.update_training_status(
            model_id,
            status,
            file_path=instance['file_path'],
            metrics=metrics
        )

        # Create version snapshot if trained and requested
        if success and status == 'trained' and create_version:
            next_version = self.version_repo.get_next_version_number(model_id)

            # Get versioned file path
            versioned_path = self.storage_manager.get_versioned_path(
                instance['user_id'],
                model_id,
                next_version,
                instance['file_extension']
            )

            # Copy current model to version directory
            import shutil
            current_path = self.storage_manager.get_absolute_from_relative(
                instance['file_path']
            )
            if self.storage_manager.file_exists(current_path):
                shutil.copy2(current_path, versioned_path)

                # Create version record
                self.version_repo.create_version(
                    model_instance_id=model_id,
                    version=next_version,
                    file_path=versioned_path,
                    metrics=metrics,
                    accuracy=metrics.get('accuracy') if metrics else None,
                    loss=metrics.get('loss') if metrics else None,
                    notes=f"Training completed at {instance.get('last_training_date')}"
                )

        return success

    def delete_model(self, model_id: int, hard_delete: bool = False) -> bool:
        """
        Delete a model (soft delete by default).

        Args:
            model_id: Model instance ID
            hard_delete: If True, permanently delete files and database record

        Returns:
            True if deleted successfully
        """
        instance = self.instance_repo.get_model_instance(model_id)

        if hard_delete:
            # Delete model file
            file_path = self.storage_manager.get_absolute_from_relative(
                instance['file_path']
            )
            if self.storage_manager.file_exists(file_path):
                self.storage_manager.delete_model_file(file_path)

            # Delete all versions
            self.version_repo.delete_versions_by_model(model_id)

            # Hard delete from database
            return self.instance_repo.hard_delete_model_instance(model_id)
        else:
            # Soft delete (archive)
            return self.instance_repo.delete_model_instance(model_id)

    def get_user_models(self, user_id: str, status: Optional[str] = None) -> List[Dict]:
        """
        Get all models for a user.

        Args:
            user_id: User identifier
            status: Optional status filter

        Returns:
            List of model instances
        """
        return self.instance_repo.get_models_by_user(user_id, status)

    def get_model_versions(self, model_id: int) -> List[Dict]:
        """
        Get all versions for a model.

        Args:
            model_id: Model instance ID

        Returns:
            List of model versions
        """
        return self.version_repo.get_versions_by_model(model_id)

    def load_model_version(self, model_id: int, version: int):
        """
        Load a specific version of a model.

        Args:
            model_id: Model instance ID
            version: Version number

        Returns:
            Loaded model instance
        """
        # Get model instance
        instance = self.instance_repo.get_model_instance(model_id)

        # Get version info
        versions = self.version_repo.get_versions_by_model(model_id)
        version_info = next((v for v in versions if v['version'] == version), None)

        if not version_info:
            raise EntityNotFoundException("Model Version", f"{model_id}_v{version}")

        # Create model and set configuration (with defensive filtering)
        model = ModelRegistry.create_model_instance(instance['model_type'])
        clean_config = {k: v for k, v in instance['config_json'].items()
                       if k not in self.EXCLUDED_CONFIG_FIELDS}
        # Filter parameters based on model type (neural network vs tree-based)
        clean_config = ModelRegistry.filter_config_for_model_type(instance['model_type'], clean_config)
        model.setModelConfigurationParam(**clean_config)

        # Load version weights
        if self.storage_manager.file_exists(version_info['file_path']):
            model.load_model(version_info['file_path'])

            # CRITICAL: Re-apply database configuration after loading weights
            # Database configuration should always take precedence over saved config
            model.setModelConfigurationParam(**clean_config)
            print(f"[VERSION LOAD] Applied database configuration for version {version}")

        return model
