"""
Model Version Repository - Database operations for model_versions table
"""
import json
from typing import Dict, List, Optional
from repositories.base_repository import BaseRepository
from core.exceptions import DatabaseException


class ModelVersionRepository(BaseRepository):
    """Repository for model_versions table operations."""

    def table_name(self) -> str:
        return "model_versions"

    def create_version(self, model_instance_id: int, version: int, file_path: str,
                      metrics: Optional[Dict] = None, accuracy: Optional[float] = None,
                      loss: Optional[float] = None, notes: Optional[str] = None,
                      created_by: Optional[str] = None) -> int:
        """
        Create a new model version.

        Args:
            model_instance_id: Reference to model_instances table
            version: Version number
            file_path: Path to versioned model file
            metrics: Training/validation metrics
            accuracy: Model accuracy
            loss: Training loss
            notes: Version notes or changelog
            created_by: User who created this version

        Returns:
            ID of newly created version
        """
        query = """
        INSERT INTO model_versions
        (model_instance_id, version, file_path, metrics_json, accuracy, loss, notes, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        metrics_str = json.dumps(metrics) if metrics else None

        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, (
                model_instance_id, version, file_path, metrics_str,
                accuracy, loss, notes, created_by
            ))
            connection.commit()
            version_id = cursor.lastrowid
            cursor.close()
            connection.close()
            return version_id
        except Exception as e:
            raise DatabaseException(f"Failed to create model version: {str(e)}", e)

    def get_version(self, version_id: int) -> Dict:
        """
        Get version by ID.

        Args:
            version_id: Version ID

        Returns:
            Version data
        """
        query = """
        SELECT id, model_instance_id, version, file_path, metrics_json,
               accuracy, loss, notes, created_at, created_by
        FROM model_versions
        WHERE id = %s
        """

        result = self.execute_query(query, (version_id,))

        if not result:
            return None

        version = result[0]
        if version.get('metrics_json'):
            version['metrics_json'] = json.loads(version['metrics_json'])

        return version

    def get_versions_by_model(self, model_instance_id: int) -> List[Dict]:
        """
        Get all versions for a model instance.

        Args:
            model_instance_id: Model instance ID

        Returns:
            List of versions ordered by version number descending
        """
        query = """
        SELECT id, version, file_path, accuracy, loss, created_at, notes
        FROM model_versions
        WHERE model_instance_id = %s
        ORDER BY version DESC
        """

        results = self.execute_query(query, (model_instance_id,))

        for result in results:
            if result.get('metrics_json'):
                result['metrics_json'] = json.loads(result['metrics_json'])

        return results

    def get_latest_version(self, model_instance_id: int) -> Optional[Dict]:
        """
        Get the latest version for a model instance.

        Args:
            model_instance_id: Model instance ID

        Returns:
            Latest version data or None
        """
        query = """
        SELECT id, version, file_path, metrics_json, accuracy, loss, created_at
        FROM model_versions
        WHERE model_instance_id = %s
        ORDER BY version DESC
        LIMIT 1
        """

        result = self.execute_query(query, (model_instance_id,))

        if not result:
            return None

        version = result[0]
        if version.get('metrics_json'):
            version['metrics_json'] = json.loads(version['metrics_json'])

        return version

    def get_next_version_number(self, model_instance_id: int) -> int:
        """
        Get the next version number for a model instance.

        Args:
            model_instance_id: Model instance ID

        Returns:
            Next version number (1 if no versions exist)
        """
        query = """
        SELECT MAX(version) as max_version
        FROM model_versions
        WHERE model_instance_id = %s
        """

        result = self.execute_query(query, (model_instance_id,))

        if result and result[0]['max_version'] is not None:
            return result[0]['max_version'] + 1
        else:
            return 1

    def delete_version(self, version_id: int) -> bool:
        """
        Delete a specific version.

        Args:
            version_id: Version ID

        Returns:
            True if deleted successfully
        """
        query = "DELETE FROM model_versions WHERE id = %s"
        rows_affected = self.execute_non_query(query, (version_id,))
        return rows_affected > 0

    def delete_versions_by_model(self, model_instance_id: int) -> int:
        """
        Delete all versions for a model instance.

        Args:
            model_instance_id: Model instance ID

        Returns:
            Number of versions deleted
        """
        query = "DELETE FROM model_versions WHERE model_instance_id = %s"
        return self.execute_non_query(query, (model_instance_id,))

    def get_version_count(self, model_instance_id: int) -> int:
        """
        Get total number of versions for a model.

        Args:
            model_instance_id: Model instance ID

        Returns:
            Version count
        """
        query = """
        SELECT COUNT(*) as count
        FROM model_versions
        WHERE model_instance_id = %s
        """

        result = self.execute_query(query, (model_instance_id,))
        return result[0]['count'] if result else 0

    def get_best_version_by_accuracy(self, model_instance_id: int) -> Optional[Dict]:
        """
        Get the version with the best accuracy.

        Args:
            model_instance_id: Model instance ID

        Returns:
            Best version data or None
        """
        query = """
        SELECT id, version, file_path, accuracy, loss, created_at
        FROM model_versions
        WHERE model_instance_id = %s AND accuracy IS NOT NULL
        ORDER BY accuracy DESC
        LIMIT 1
        """

        result = self.execute_query(query, (model_instance_id,))
        return result[0] if result else None

    def get_best_version_by_loss(self, model_instance_id: int) -> Optional[Dict]:
        """
        Get the version with the lowest loss.

        Args:
            model_instance_id: Model instance ID

        Returns:
            Best version data or None
        """
        query = """
        SELECT id, version, file_path, accuracy, loss, created_at
        FROM model_versions
        WHERE model_instance_id = %s AND loss IS NOT NULL
        ORDER BY loss ASC
        LIMIT 1
        """

        result = self.execute_query(query, (model_instance_id,))
        return result[0] if result else None
