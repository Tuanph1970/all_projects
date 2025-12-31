"""
Model Instance Repository - Database operations for model_instances table
"""
import json
from typing import Dict, List, Optional
from repositories.base_repository import BaseRepository
from core.exceptions import DatabaseException, EntityNotFoundException


class ModelInstanceRepository(BaseRepository):
    """Repository for model_instances table operations."""

    def table_name(self) -> str:
        return "model_instances"

    def create_model_instance(self, model_type: str, model_sub_type: Optional[str],
                             model_name: str, user_id: str, config_json: dict,
                             file_extension: str, past_covariate: bool = False,
                             future_covariate: bool = False,
                             created_by: Optional[str] = None) -> int:
        """
        Create a new model instance.

        Args:
            model_type: Type of model (BlockRNN, NBeats, etc.)
            model_sub_type: Sub-type (LSTM, GRU, etc.)
            model_name: User-defined model name
            user_id: Owner of the model
            config_json: Complete configuration parameters as dict
            file_extension: File extension (.pt or .pkl)
            past_covariate: Whether model uses past covariates
            future_covariate: Whether model uses future covariates
            created_by: User who created the model

        Returns:
            ID of newly created model instance
        """
        query = """
        INSERT INTO model_instances
        (model_type, model_sub_type, model_name, user_id, status, config_json,
         file_extension, past_covariate, future_covariate, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        config_str = json.dumps(config_json)

        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, (
                model_type, model_sub_type, model_name, user_id, 'created',
                config_str, file_extension, past_covariate, future_covariate,
                created_by or user_id
            ))
            connection.commit()
            model_id = cursor.lastrowid
            cursor.close()
            connection.close()
            return model_id
        except Exception as e:
            raise DatabaseException(f"Failed to create model instance: {str(e)}", e)

    def get_model_instance(self, model_id: int) -> Dict:
        """
        Get model instance by ID.

        Args:
            model_id: Model instance ID

        Returns:
            Model instance data as dictionary

        Raises:
            EntityNotFoundException: If model not found
        """
        query = """
        SELECT id, model_type, model_sub_type, model_name, user_id, status,
               config_json, file_path, file_extension, last_training_date,
               training_metrics_json, past_covariate, future_covariate,
               created_at, updated_at, created_by
        FROM model_instances
        WHERE id = %s
        """

        result = self.execute_query(query, (model_id,))

        if not result:
            raise EntityNotFoundException("Model Instance", model_id)

        instance = result[0]
        # Parse JSON fields
        if instance.get('config_json'):
            instance['config_json'] = json.loads(instance['config_json'])
        if instance.get('training_metrics_json'):
            instance['training_metrics_json'] = json.loads(instance['training_metrics_json'])

        return instance

    def update_model_instance(self, model_id: int, **kwargs) -> bool:
        """
        Update model instance fields.

        Args:
            model_id: Model instance ID
            **kwargs: Fields to update (config_json, status, file_path, etc.)

        Returns:
            True if updated successfully
        """
        allowed_fields = {
            'model_name', 'model_sub_type', 'status', 'config_json', 'file_path',
            'last_training_date', 'training_metrics_json'
        }

        updates = []
        params = []

        for key, value in kwargs.items():
            if key in allowed_fields:
                if key in ['config_json', 'training_metrics_json'] and isinstance(value, dict):
                    value = json.dumps(value)
                updates.append(f"{key} = %s")
                params.append(value)

        if not updates:
            return False

        query = f"UPDATE model_instances SET {', '.join(updates)} WHERE id = %s"
        params.append(model_id)

        rows_affected = self.execute_non_query(query, tuple(params))
        return rows_affected > 0

    def delete_model_instance(self, model_id: int) -> bool:
        """
        Delete model instance (soft delete by setting status to 'archived').

        Args:
            model_id: Model instance ID

        Returns:
            True if deleted successfully
        """
        query = "UPDATE model_instances SET status = 'archived' WHERE id = %s"
        rows_affected = self.execute_non_query(query, (model_id,))
        return rows_affected > 0

    def hard_delete_model_instance(self, model_id: int) -> bool:
        """
        Permanently delete model instance.

        Args:
            model_id: Model instance ID

        Returns:
            True if deleted successfully
        """
        query = "DELETE FROM model_instances WHERE id = %s"
        rows_affected = self.execute_non_query(query, (model_id,))
        return rows_affected > 0

    def get_models_by_user(self, user_id: str, status: Optional[str] = None) -> List[Dict]:
        """
        Get all models for a specific user.

        Args:
            user_id: User identifier
            status: Optional status filter

        Returns:
            List of model instances
        """
        if status:
            query = """
            SELECT id, model_type, model_sub_type, model_name, status, file_path,
                   last_training_date, created_at, updated_at
            FROM model_instances
            WHERE user_id = %s AND status = %s
            ORDER BY created_at DESC
            """
            return self.execute_query(query, (user_id, status))
        else:
            query = """
            SELECT id, model_type, model_sub_type, model_name, status, file_path,
                   last_training_date, created_at, updated_at
            FROM model_instances
            WHERE user_id = %s AND status != 'archived'
            ORDER BY created_at DESC
            """
            return self.execute_query(query, (user_id,))

    def get_models_by_type(self, model_type: str, user_id: Optional[str] = None) -> List[Dict]:
        """
        Get models by type, optionally filtered by user.

        Args:
            model_type: Model type to filter
            user_id: Optional user filter

        Returns:
            List of model instances
        """
        if user_id:
            query = """
            SELECT id, model_type, model_sub_type, model_name, status, user_id,
                   last_training_date, created_at
            FROM model_instances
            WHERE model_type = %s AND user_id = %s AND status != 'archived'
            ORDER BY created_at DESC
            """
            return self.execute_query(query, (model_type, user_id))
        else:
            query = """
            SELECT id, model_type, model_sub_type, model_name, status, user_id,
                   last_training_date, created_at
            FROM model_instances
            WHERE model_type = %s AND status != 'archived'
            ORDER BY created_at DESC
            """
            return self.execute_query(query, (model_type,))

    def update_training_status(self, model_id: int, status: str,
                               file_path: Optional[str] = None,
                               metrics: Optional[Dict] = None) -> bool:
        """
        Update model training status and related fields.

        Args:
            model_id: Model instance ID
            status: New status (training, trained, failed)
            file_path: Path to trained model file
            metrics: Training metrics

        Returns:
            True if updated successfully
        """
        updates = ['status = %s']
        params = [status]

        if status == 'trained':
            updates.append('last_training_date = NOW()')

        if file_path:
            updates.append('file_path = %s')
            params.append(file_path)

        if metrics:
            updates.append('training_metrics_json = %s')
            params.append(json.dumps(metrics))

        query = f"UPDATE model_instances SET {', '.join(updates)} WHERE id = %s"
        params.append(model_id)

        rows_affected = self.execute_non_query(query, tuple(params))
        return rows_affected > 0

    def search_models(self, search_term: str, user_id: Optional[str] = None) -> List[Dict]:
        """
        Search models by name.

        Args:
            search_term: Search term
            user_id: Optional user filter

        Returns:
            List of matching model instances
        """
        search_pattern = f"%{search_term}%"

        if user_id:
            query = """
            SELECT id, model_type, model_sub_type, model_name, status,
                   created_at, updated_at
            FROM model_instances
            WHERE model_name LIKE %s AND user_id = %s AND status != 'archived'
            ORDER BY created_at DESC
            """
            return self.execute_query(query, (search_pattern, user_id))
        else:
            query = """
            SELECT id, model_type, model_sub_type, model_name, status, user_id,
                   created_at, updated_at
            FROM model_instances
            WHERE model_name LIKE %s AND status != 'archived'
            ORDER BY created_at DESC
            """
            return self.execute_query(query, (search_pattern,))
