"""
Model Capability Repository - Database operations for tbl_model_capabilities table
"""
from typing import Dict, List, Optional
from repositories.base_repository import BaseRepository
from core.exceptions import EntityNotFoundException


class ModelCapabilityRepository(BaseRepository):
    """Repository for model_capabilities table operations."""

    def table_name(self) -> str:
        return "tbl_model_capabilities"

    def get_capabilities_by_model_type(self, model_type: str) -> Optional[Dict]:
        """
        Get covariate capabilities for a specific model type.

        Args:
            model_type: Type of model (DLinear, RNN, etc.)

        Returns:
            Dict with capability information or None if not found
            {
                'id': int,
                'model_type': str,
                'supports_past_covariates': bool,
                'supports_future_covariates': bool,
                'description': str,
                'is_active': bool
            }

        Raises:
            EntityNotFoundException: If model type not found
        """
        query = """
        SELECT id, model_type, supports_past_covariates, supports_future_covariates,
               description, is_active, created_at, updated_at
        FROM tbl_model_capabilities
        WHERE model_type = %s AND is_active = 1
        """

        result = self.execute_query(query, (model_type,))

        if not result:
            raise EntityNotFoundException("Model Capability", model_type)

        capability = result[0]
        # Convert TINYINT to boolean for clarity
        capability['supports_past_covariates'] = bool(capability['supports_past_covariates'])
        capability['supports_future_covariates'] = bool(capability['supports_future_covariates'])
        capability['is_active'] = bool(capability['is_active'])

        return capability

    def get_all_capabilities(self, active_only: bool = True) -> List[Dict]:
        """
        Get all model capabilities.

        Args:
            active_only: If True, only return active model types

        Returns:
            List of capability dictionaries
        """
        if active_only:
            query = """
            SELECT id, model_type, supports_past_covariates, supports_future_covariates,
                   description, is_active, created_at, updated_at
            FROM tbl_model_capabilities
            WHERE is_active = 1
            ORDER BY model_type
            """
            results = self.execute_query(query)
        else:
            query = """
            SELECT id, model_type, supports_past_covariates, supports_future_covariates,
                   description, is_active, created_at, updated_at
            FROM tbl_model_capabilities
            ORDER BY model_type
            """
            results = self.execute_query(query)

        # Convert TINYINT to boolean
        for capability in results:
            capability['supports_past_covariates'] = bool(capability['supports_past_covariates'])
            capability['supports_future_covariates'] = bool(capability['supports_future_covariates'])
            capability['is_active'] = bool(capability['is_active'])

        return results

    def check_covariate_support(self, model_type: str, covariate_type: str) -> bool:
        """
        Check if a model type supports a specific covariate type.

        Args:
            model_type: Type of model (DLinear, RNN, etc.)
            covariate_type: 'past', 'future', or 'both'

        Returns:
            True if the model supports the covariate type, False otherwise
        """
        try:
            capabilities = self.get_capabilities_by_model_type(model_type)
        except EntityNotFoundException:
            # If model type not found in capabilities table, return False
            return False

        supports_past = capabilities['supports_past_covariates']
        supports_future = capabilities['supports_future_covariates']

        if covariate_type == 'past':
            return supports_past
        elif covariate_type == 'future':
            return supports_future
        elif covariate_type == 'both':
            return supports_past and supports_future
        else:
            return False

    def get_models_by_covariate_support(self, covariate_type: str) -> List[str]:
        """
        Get list of model types that support a specific covariate type.

        Args:
            covariate_type: 'past', 'future', or 'both'

        Returns:
            List of model type names
        """
        if covariate_type == 'past':
            query = """
            SELECT model_type
            FROM tbl_model_capabilities
            WHERE supports_past_covariates = 1 AND is_active = 1
            ORDER BY model_type
            """
        elif covariate_type == 'future':
            query = """
            SELECT model_type
            FROM tbl_model_capabilities
            WHERE supports_future_covariates = 1 AND is_active = 1
            ORDER BY model_type
            """
        elif covariate_type == 'both':
            query = """
            SELECT model_type
            FROM tbl_model_capabilities
            WHERE supports_past_covariates = 1 AND supports_future_covariates = 1 AND is_active = 1
            ORDER BY model_type
            """
        else:
            return []

        results = self.execute_query(query)
        return [row['model_type'] for row in results]

    def create_capability(self, model_type: str, supports_past: bool,
                         supports_future: bool, description: str = None) -> int:
        """
        Create a new model capability entry.

        Args:
            model_type: Type of model
            supports_past: Whether model supports past covariates
            supports_future: Whether model supports future covariates
            description: Optional description

        Returns:
            ID of newly created capability record
        """
        query = """
        INSERT INTO tbl_model_capabilities
        (model_type, supports_past_covariates, supports_future_covariates, description)
        VALUES (%s, %s, %s, %s)
        """

        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, (model_type, supports_past, supports_future, description))
            connection.commit()
            capability_id = cursor.lastrowid
            return capability_id
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def update_capability(self, model_type: str, supports_past: bool = None,
                         supports_future: bool = None, description: str = None,
                         is_active: bool = None) -> bool:
        """
        Update model capability information.

        Args:
            model_type: Type of model to update
            supports_past: Optional new value for past covariate support
            supports_future: Optional new value for future covariate support
            description: Optional new description
            is_active: Optional new active status

        Returns:
            True if updated successfully
        """
        updates = []
        params = []

        if supports_past is not None:
            updates.append("supports_past_covariates = %s")
            params.append(supports_past)

        if supports_future is not None:
            updates.append("supports_future_covariates = %s")
            params.append(supports_future)

        if description is not None:
            updates.append("description = %s")
            params.append(description)

        if is_active is not None:
            updates.append("is_active = %s")
            params.append(is_active)

        if not updates:
            return False

        params.append(model_type)
        query = f"UPDATE tbl_model_capabilities SET {', '.join(updates)} WHERE model_type = %s"

        rows_affected = self.execute_non_query(query, tuple(params))
        return rows_affected > 0

    def delete_capability(self, model_type: str, soft_delete: bool = True) -> bool:
        """
        Delete a model capability (soft delete by default).

        Args:
            model_type: Type of model to delete
            soft_delete: If True, set is_active=0; if False, permanently delete

        Returns:
            True if deleted successfully
        """
        if soft_delete:
            query = "UPDATE tbl_model_capabilities SET is_active = 0 WHERE model_type = %s"
        else:
            query = "DELETE FROM tbl_model_capabilities WHERE model_type = %s"

        rows_affected = self.execute_non_query(query, (model_type,))
        return rows_affected > 0

    def get_capability_summary(self) -> Dict:
        """
        Get summary statistics of model capabilities.

        Returns:
            Dict with summary information
            {
                'total_models': int,
                'past_only': int,
                'future_only': int,
                'both': int,
                'none': int
            }
        """
        query = """
        SELECT
            COUNT(*) as total_models,
            SUM(CASE WHEN supports_past_covariates = 1 AND supports_future_covariates = 0 THEN 1 ELSE 0 END) as past_only,
            SUM(CASE WHEN supports_past_covariates = 0 AND supports_future_covariates = 1 THEN 1 ELSE 0 END) as future_only,
            SUM(CASE WHEN supports_past_covariates = 1 AND supports_future_covariates = 1 THEN 1 ELSE 0 END) as both,
            SUM(CASE WHEN supports_past_covariates = 0 AND supports_future_covariates = 0 THEN 1 ELSE 0 END) as none
        FROM tbl_model_capabilities
        WHERE is_active = 1
        """

        result = self.execute_query(query)
        return result[0] if result else {}

    def validate_model_type_exists(self, model_type: str) -> bool:
        """
        Check if a model type exists in the capabilities table.

        Args:
            model_type: Type of model to check

        Returns:
            True if model type exists and is active
        """
        query = """
        SELECT COUNT(*) as count
        FROM tbl_model_capabilities
        WHERE model_type = %s AND is_active = 1
        """

        result = self.execute_query(query, (model_type,))
        return result[0]['count'] > 0 if result else False
