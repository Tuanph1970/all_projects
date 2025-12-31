"""
Repository for managing available prediction model types.
Provides database access to tbl_all_models and tbl_model_sub_types.
"""

from typing import Dict, List, Optional
from repositories.base_repository import BaseRepository


class AllModelsRepository(BaseRepository):
    """Repository for querying available model types and their sub-types."""

    def table_name(self) -> str:
        """Primary table name for model types."""
        return "tbl_all_models"

    def get_all_model_types(self, active_only: bool = True) -> List[Dict]:
        """
        Get all available model types.

        Args:
            active_only: If True, only return active models (default: True)

        Returns:
            List of model type dictionaries with keys: id, name, description,
            has_sub_models, is_active, display_order
        """
        query = f"SELECT * FROM {self.table_name()}"

        if active_only:
            query += " WHERE is_active = 1"

        query += " ORDER BY display_order ASC, name ASC"

        return self.execute_query(query)

    def get_model_type_by_name(self, model_name: str) -> Optional[Dict]:
        """
        Get a specific model type by name.

        Args:
            model_name: The model type name (e.g., 'BlockRNN', 'RNN')

        Returns:
            Model type dictionary or None if not found
        """
        query = f"SELECT * FROM {self.table_name()} WHERE name = %s"
        result = self.execute_query(query, (model_name,))

        return result[0] if result else None

    def get_model_sub_types(self, model_id: int, active_only: bool = True) -> List[Dict]:
        """
        Get all sub-types for a specific model.

        Args:
            model_id: The model ID from tbl_all_models
            active_only: If True, only return active sub-types (default: True)

        Returns:
            List of sub-type dictionaries
        """
        query = "SELECT * FROM tbl_model_sub_types WHERE model_id = %s"

        if active_only:
            query += " AND is_active = 1"

        query += " ORDER BY display_order ASC, name ASC"

        return self.execute_query(query, (model_id,))

    def get_all_models_with_subtypes(self, active_only: bool = True) -> List[Dict]:
        """
        Get all model types with their sub-types in a structured format.
        Uses the v_all_models_with_subtypes view for efficient querying.

        Args:
            active_only: If True, only return active models (default: True)

        Returns:
            List of model dictionaries, each with a 'sub_model' array
            Format matches the original get_all_predict_model() structure:
            [
                {
                    'name': 'BlockRNN',
                    'sub_model': [{'name': 'LSTM'}, {'name': 'GRU'}, {'name': 'Vanilla'}]
                },
                ...
            ]
        """
        query = """
        SELECT
            model_id,
            model_name,
            model_description,
            has_sub_models,
            model_active,
            model_display_order,
            subtype_id,
            subtype_name,
            subtype_description,
            subtype_active,
            subtype_display_order
        FROM v_all_models_with_subtypes
        """

        if active_only:
            query += " WHERE model_active = 1"

        query += " ORDER BY model_display_order, subtype_display_order"

        results = self.execute_query(query)

        # Transform results into the expected structure
        models_dict = {}

        for row in results:
            model_name = row['model_name']

            # Initialize model entry if not exists
            if model_name not in models_dict:
                models_dict[model_name] = {
                    'name': model_name,
                    'sub_model': []
                }

            # Add sub-model if exists
            if row['subtype_name']:
                models_dict[model_name]['sub_model'].append({
                    'name': row['subtype_name']
                })

        # Convert dict to list, maintaining order
        return list(models_dict.values())

    def add_model_type(self, name: str, description: str = None,
                      has_sub_models: bool = False, is_active: bool = True,
                      display_order: int = 0) -> int:
        """
        Add a new model type.

        Args:
            name: Model type name (must be unique)
            description: Optional description
            has_sub_models: Whether this model has sub-types
            is_active: Whether the model is active
            display_order: Display order in UI

        Returns:
            ID of the newly created model type
        """
        query = f"""
        INSERT INTO {self.table_name()}
        (name, description, has_sub_models, is_active, display_order)
        VALUES (%s, %s, %s, %s, %s)
        """
        params = (name, description, has_sub_models, is_active, display_order)

        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, params)
            connection.commit()
            return cursor.lastrowid
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def update_model_type(self, model_id: int, **kwargs) -> bool:
        """
        Update a model type.

        Args:
            model_id: The model ID to update
            **kwargs: Fields to update (name, description, has_sub_models,
                     is_active, display_order)

        Returns:
            True if update was successful, False otherwise
        """
        allowed_fields = ['name', 'description', 'has_sub_models',
                         'is_active', 'display_order']
        update_fields = []
        params = []

        for field in allowed_fields:
            if field in kwargs:
                update_fields.append(f"{field} = %s")
                params.append(kwargs[field])

        if not update_fields:
            return False

        params.append(model_id)
        query = f"UPDATE {self.table_name()} SET {', '.join(update_fields)} WHERE id = %s"

        return self.execute_non_query(query, tuple(params)) > 0

    def delete_model_type(self, model_id: int, soft_delete: bool = True) -> bool:
        """
        Delete a model type (soft or hard delete).

        Args:
            model_id: The model ID to delete
            soft_delete: If True, set is_active=0; if False, actually delete

        Returns:
            True if successful, False otherwise
        """
        if soft_delete:
            return self.update_model_type(model_id, is_active=False)
        else:
            # Hard delete (will cascade to sub-types due to FK constraint)
            query = f"DELETE FROM {self.table_name()} WHERE id = %s"
            return self.execute_non_query(query, (model_id,)) > 0

    def add_model_subtype(self, model_id: int, name: str,
                         description: str = None, is_active: bool = True,
                         display_order: int = 0) -> int:
        """
        Add a sub-type to an existing model.

        Args:
            model_id: Parent model ID
            name: Sub-type name (e.g., 'LSTM', 'GRU')
            description: Optional description
            is_active: Whether the sub-type is active
            display_order: Display order in UI

        Returns:
            ID of the newly created sub-type
        """
        query = """
        INSERT INTO tbl_model_sub_types
        (model_id, name, description, is_active, display_order)
        VALUES (%s, %s, %s, %s, %s)
        """
        params = (model_id, name, description, is_active, display_order)

        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, params)
            connection.commit()
            return cursor.lastrowid
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
