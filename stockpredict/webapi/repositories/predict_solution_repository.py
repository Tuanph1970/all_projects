from typing import Dict, List, Optional
import datetime
import pandas as pd
from repositories.base_repository import BaseRepository


class PredictSolutionRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_solution"
    
    # Train status constants
    TRAIN_STATUS_NOT_TRAINED = 'not_trained'
    TRAIN_STATUS_TRAINED = 'trained'
    TRAIN_STATUS_PREDICTED = 'predicted'

    def get_solutions(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        Get all solutions, optionally filtered by user.

        Args:
            user_id: Optional user filter

        Returns:
            List of solution information
        """
        query = """
        SELECT
            tbl_solution.id,
            tbl_solution.solution_name,
            tbl_solution.ticker,
            tbl_solution.created_by,
            tbl_solution.user_id,
            tbl_solution.created_date,
            tbl_solution.updated_date,
            tbl_solution.train_status,
            model_instances.model_type,
            model_instances.model_sub_type,
            model_instances.model_name
        FROM tbl_solution
        INNER JOIN model_instances ON tbl_solution.model_id = model_instances.id
        """

        if user_id:
            query += " WHERE tbl_solution.user_id = %s"
            return self.execute_query(query, (user_id,))
        else:
            return self.execute_query(query)

    def get_trained_solutions(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        Get all trained solutions (solution_status = 1), optionally filtered by user.

        Args:
            user_id: Optional user filter

        Returns:
            List of trained solution information
        """
        query = """
        SELECT
            tbl_solution.id,
            tbl_solution.solution_name,
            tbl_solution.ticker,
            tbl_solution.model_id,
            tbl_solution.created_by,
            tbl_solution.user_id,
            tbl_solution.created_date,
            tbl_solution.start_training_date,
            tbl_solution.end_training_date,
            tbl_solution.solution_status,
            model_instances.model_type,
            model_instances.model_name
        FROM tbl_solution
        INNER JOIN model_instances ON tbl_solution.model_id = model_instances.id
        WHERE tbl_solution.solution_status = 1
        """

        if user_id:
            query += " AND tbl_solution.user_id = %s"
            return self.execute_query(query, (user_id,))
        else:
            return self.execute_query(query)
    
    def get_predict_models(self) -> List[Dict]:
        """
        Get all available models for solution creation.
        Returns all model fields needed by frontend dropdown.
        """
        query = """
        SELECT
            id,
            model_name,
            model_type,
            model_sub_type,
            past_covariate,
            future_covariate
        FROM model_instances
        ORDER BY id DESC
        """
        return self.execute_query(query)
    
    def get_predict_covariates(self) -> List[Dict]:
        query = "SELECT id, series_name FROM tbl_time_series WHERE status = 1"
        return self.execute_query(query)
    
    def create_predict_solution(self, data: Dict) -> int:
        """
        Create a new prediction solution

        New schema: Uses solution_indicators instead of time_series_solution
        Supports train_validation_ratio configuration
        """
        query = """
        INSERT INTO tbl_solution
        (solution_name, model_id, ticker, created_date, created_by, user_id, status,
         start_training_date, end_training_date, train_validation_ratio, solution_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        # Use user_id or fall back to created_by
        user_id = data.get('user_id') or data.get('created_by')

        params = (
            data['solution_name'],
            data['model_id'],
            data['ticker'],
            data['created_date'],
            data['created_by'],
            user_id,
            data.get('status', 1),
            data.get('start_training_date'),
            data.get('end_training_date'),
            data.get('train_validation_ratio', 0.8),
            0  # solution_status: 0=not trained
        )

        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, params)
            connection.commit()
            solution_id = cursor.lastrowid

            # Note: Indicators are added separately via IndicatorRepository
            # This keeps the concerns separated and code cleaner

            return solution_id
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def update_training_solution(self, solution_id: int, start_training_date: str, end_training_date: str) -> bool:
        query = """
        UPDATE tbl_solution
        SET start_training_date = %s, end_training_date = %s, solution_status = 1, train_status = %s
        WHERE id = %s
        """
        return self.execute_non_query(query, (start_training_date, end_training_date, self.TRAIN_STATUS_TRAINED, solution_id)) > 0

    def update_train_status(self, solution_id: int, train_status: str) -> bool:
        """
        Update the train_status of a solution.

        Args:
            solution_id: Solution ID
            train_status: One of 'not_trained', 'trained', 'predicted'

        Returns:
            True if updated successfully
        """
        valid_statuses = [self.TRAIN_STATUS_NOT_TRAINED, self.TRAIN_STATUS_TRAINED, self.TRAIN_STATUS_PREDICTED]
        if train_status not in valid_statuses:
            raise ValueError(f"Invalid train_status: {train_status}. Must be one of {valid_statuses}")

        query = "UPDATE tbl_solution SET train_status = %s WHERE id = %s"
        return self.execute_non_query(query, (train_status, solution_id)) > 0
    
    def update_predict_solution(self, data: Dict) -> bool:
        """
        Update a prediction solution

        New schema: Simplified update, indicators managed separately
        """
        solution_id = data['id']

        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            # Update solution
            update_query = """
            UPDATE tbl_solution
            SET solution_name = %s, model_id = %s, ticker = %s,
                updated_date = %s, updated_by = %s,
                start_training_date = %s, end_training_date = %s,
                train_validation_ratio = %s, user_id = %s
            WHERE id = %s
            """
            # Use user_id or fall back to updated_by
            user_id = data.get('user_id') or data.get('updated_by')

            params = (
                data['solution_name'],
                data['model_id'],
                data['ticker'],
                data['updated_date'],
                data['updated_by'],
                data.get('start_training_date'),
                data.get('end_training_date'),
                data.get('train_validation_ratio', 0.8),
                user_id,
                solution_id
            )
            cursor.execute(update_query, params)

            # Note: Indicators are updated separately via IndicatorRepository
            # This separation of concerns makes the code more maintainable

            connection.commit()
            return True
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def get_solution_by_id(self, solution_id: int) -> Dict:
        """
        Get solution by ID

        New schema: Simplified query, indicators retrieved separately
        """
        query = "SELECT * FROM tbl_solution WHERE id = %s"
        result = self.execute_query(query, (solution_id,))

        if not result:
            return {}

        solution_data = result[0]

        # Note: Indicators are retrieved separately via IndicatorRepository.get_solution_indicators()
        # This provides better separation of concerns and clearer code structure

        return solution_data
    
    def delete_solution_by_id(self, solution_id: int) -> bool:
        """
        Delete solution by ID

        New schema: Also deletes associated solution_indicators
        """
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            # Delete solution_indicators (CASCADE should handle this if FK is set, but explicit is safer)
            cursor.execute("DELETE FROM solution_indicators WHERE solution_id = %s", (solution_id,))

            # Delete solution
            cursor.execute("DELETE FROM tbl_solution WHERE id = %s", (solution_id,))

            connection.commit()
            return True
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()


class TimeSeriesSolutionRepository(BaseRepository):
    def table_name(self) -> str:
        return "time_series_solution"