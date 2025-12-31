"""
Model Storage Manager - Centralized File Storage Management
Handles all file path operations with user-specific folder organization
"""
import os
from typing import Optional
from pathlib import Path
from core.exceptions import StorageException


class ModelStorageManager:
    """
    Centralized manager for model file storage operations.
    Implements user-specific folder structure: users_model/{user_id}/model_{model_id}.ext
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize storage manager.

        Args:
            base_path: Base directory for model storage. Defaults to environment
                      variable MODEL_STORAGE_PATH or './users_model'
        """
        self.base_path = base_path or os.getenv('MODEL_STORAGE_PATH', './users_model')
        self._ensure_base_directory()

    def _ensure_base_directory(self):
        """Create base directory if it doesn't exist."""
        try:
            Path(self.base_path).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise StorageException(f"Failed to create base directory: {str(e)}", e)

    def get_user_directory(self, user_id: str) -> str:
        """
        Get user-specific directory path.

        Args:
            user_id: User identifier

        Returns:
            Absolute path to user directory
        """
        user_dir = os.path.join(self.base_path, str(user_id))
        Path(user_dir).mkdir(parents=True, exist_ok=True)
        return user_dir

    def get_model_file_path(self, user_id: str, model_id: int, file_extension: str) -> str:
        """
        Get absolute file path for a model.

        Args:
            user_id: User identifier
            model_id: Model instance ID
            file_extension: File extension (.pt or .pkl)

        Returns:
            Absolute path to model file
        """
        user_dir = self.get_user_directory(user_id)
        filename = f"model_{model_id}{file_extension}"
        return os.path.join(user_dir, filename)

    def get_relative_path(self, user_id: str, model_id: int, file_extension: str) -> str:
        """
        Get relative file path for database storage.

        Args:
            user_id: User identifier
            model_id: Model instance ID
            file_extension: File extension

        Returns:
            Relative path from base_path (e.g., 'user123/model_456.pt')
        """
        return os.path.join(str(user_id), f"model_{model_id}{file_extension}")

    def get_absolute_from_relative(self, relative_path: str) -> str:
        """
        Convert relative path to absolute path.

        Args:
            relative_path: Relative path from base_path

        Returns:
            Absolute file path
        """
        return os.path.join(self.base_path, relative_path)

    def file_exists(self, file_path: str) -> bool:
        """
        Check if a model file exists.

        Args:
            file_path: Path to check (absolute or relative)

        Returns:
            True if file exists, False otherwise
        """
        # Convert to absolute path to handle both relative and ./relative paths
        absolute_file_path = os.path.abspath(file_path)
        return os.path.isfile(absolute_file_path)

    def delete_model_file(self, file_path: str) -> bool:
        """
        Delete a model file.

        Args:
            file_path: Path to file (absolute or relative)

        Returns:
            True if deleted successfully, False if file doesn't exist

        Raises:
            StorageException: If deletion fails
        """
        # Convert to absolute path to handle both relative and ./relative paths
        absolute_file_path = os.path.abspath(file_path)

        if not os.path.exists(absolute_file_path):
            return False

        try:
            os.remove(absolute_file_path)
            return True
        except Exception as e:
            raise StorageException(f"Failed to delete file: {str(e)}", e)

    def get_versioned_path(self, user_id: str, model_id: int, version: int,
                          file_extension: str) -> str:
        """
        Get path for a specific model version.

        Args:
            user_id: User identifier
            model_id: Model instance ID
            version: Version number
            file_extension: File extension

        Returns:
            Absolute path to versioned model file
        """
        user_dir = self.get_user_directory(user_id)
        versions_dir = os.path.join(user_dir, f"model_{model_id}_versions")
        Path(versions_dir).mkdir(parents=True, exist_ok=True)

        filename = f"model_{model_id}_v{version}{file_extension}"
        return os.path.join(versions_dir, filename)

    def get_user_models_list(self, user_id: str) -> list:
        """
        List all model files for a user.

        Args:
            user_id: User identifier

        Returns:
            List of model filenames
        """
        user_dir = self.get_user_directory(user_id)
        try:
            files = [f for f in os.listdir(user_dir)
                    if os.path.isfile(os.path.join(user_dir, f))
                    and (f.endswith('.pt') or f.endswith('.pkl'))]
            return files
        except Exception as e:
            raise StorageException(f"Failed to list user models: {str(e)}", e)

    def get_directory_size(self, user_id: str) -> int:
        """
        Calculate total storage size for a user's models.

        Args:
            user_id: User identifier

        Returns:
            Total size in bytes
        """
        user_dir = self.get_user_directory(user_id)
        total_size = 0

        try:
            for dirpath, dirnames, filenames in os.walk(user_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.isfile(filepath):
                        total_size += os.path.getsize(filepath)
            return total_size
        except Exception as e:
            raise StorageException(f"Failed to calculate directory size: {str(e)}", e)

    def cleanup_user_directory(self, user_id: str, keep_active: bool = True):
        """
        Clean up user directory (for maintenance/testing).

        Args:
            user_id: User identifier
            keep_active: If True, only remove backup/temp files

        Raises:
            StorageException: If cleanup fails
        """
        user_dir = self.get_user_directory(user_id)

        try:
            if keep_active:
                # Remove only version directories and temp files
                for item in os.listdir(user_dir):
                    item_path = os.path.join(user_dir, item)
                    if os.path.isdir(item_path) and '_versions' in item:
                        import shutil
                        shutil.rmtree(item_path)
            else:
                # Remove entire user directory
                import shutil
                shutil.rmtree(user_dir)
        except Exception as e:
            raise StorageException(f"Failed to cleanup directory: {str(e)}", e)
