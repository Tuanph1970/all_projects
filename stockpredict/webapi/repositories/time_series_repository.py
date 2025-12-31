from typing import Dict, List, Optional
from datetime import datetime
from repositories.base_repository import BaseRepository


class TimeSeriesRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_time_series"
    
    def add_time_series(self, data: Dict) -> bool:
        query = """
        INSERT INTO tbl_time_series
        (indicator_id, series_name, end_date, status, created_date, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            data['indicator_id'], data['series_name'],
            data.get('end_date'), data['status'], data['created_date'], data['created_by']
        )
        return self.execute_non_query(query, params) > 0
    
    def modify_time_series(self, data: Dict) -> bool:
        query = """
        UPDATE tbl_time_series
        SET indicator_id = %s, series_name = %s, end_date = %s, updated_date = %s
        WHERE id = %s
        """
        params = (
            data['indicator_id'], data['series_name'],
            data.get('end_date'), data['updated_date'], data['id']
        )
        return self.execute_non_query(query, params) > 0
    
    def get_all_time_series(self) -> List[Dict]:
        query = """
        SELECT
            ti.id as indicator_id,
            ti.name as indicator_name,
            ti.type as indicator_type,
            ti.description as indicator_description,
            ti.default_parameters,
            ts.id,
            ts.series_name,
            ts.end_date,
            ts.created_date,
            ts.created_by
        FROM technical_indicators ti
        INNER JOIN tbl_time_series ts ON ti.id = ts.indicator_id
        WHERE ts.status = 1
        ORDER BY ts.created_date DESC
        """
        return self.execute_query(query)
    
    def get_series_by_id(self, series_id: int) -> Optional[Dict]:
        query = """
        SELECT
            ts.id,
            ts.indicator_id,
            ti.name as indicator_name,
            ti.type as indicator_type,
            ti.description as indicator_description,
            ti.default_parameters,
            ts.series_name,
            ts.end_date,
            ts.created_date,
            ts.created_by
        FROM technical_indicators ti
        INNER JOIN tbl_time_series ts ON ti.id = ts.indicator_id
        WHERE ts.id = %s
        """
        result = self.execute_query(query, (series_id,))
        return result[0] if result else None
    
    def delete_series_by_id(self, series_id: int) -> int:
        # Check if series is used in solutions
        check_query = "SELECT time_series_id FROM time_series_solution WHERE time_series_id = %s"
        check_result = self.execute_query(check_query, (series_id,))
        
        if not check_result:
            delete_query = f"DELETE FROM {self.table_name()} WHERE id = %s"
            self.execute_non_query(delete_query, (series_id,))
            return 0  # Successfully deleted
        else:
            return 1  # Cannot delete, referenced by solutions
    
    def get_series_by_ids(self, time_series_ids: List[int]) -> List[Dict]:
        if not time_series_ids:
            return []

        placeholders = ', '.join(['%s'] * len(time_series_ids))
        query = f"""
        SELECT
            ts.id,
            ts.indicator_id,
            ti.name as indicator_name,
            ti.type as indicator_type,
            ti.description as indicator_description,
            ti.default_parameters,
            ts.series_name,
            ts.end_date,
            ts.created_date,
            ts.created_by
        FROM technical_indicators ti
        INNER JOIN tbl_time_series ts ON ti.id = ts.indicator_id
        WHERE ts.id IN ({placeholders})
        AND ts.status = 1
        """
        return self.execute_query(query, tuple(time_series_ids))
    
    def update_series_batch(self, series_data: List[Dict]) -> bool:
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            for series in series_data:
                query = """
                UPDATE tbl_time_series
                SET end_date = %s, indicator_id = %s
                WHERE id = %s
                """
                cursor.execute(query, (series.get('end_date'), series.get('indicator_id'), series['id']))

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


class SeriesTypeRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_series_type"
    
    def get_series_types(self) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()}"
        return self.execute_query(query)