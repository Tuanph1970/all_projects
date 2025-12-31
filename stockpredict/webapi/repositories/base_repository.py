from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar
import pandas as pd
import pymysql
from core.database import get_database_connection
from core.exceptions import DatabaseException

T = TypeVar('T')


class BaseRepository(ABC):
    def __init__(self):
        pass
    
    def get_connection(self) -> pymysql.Connection:
        return get_database_connection()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, params or ())
            
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            else:
                return []
        except Exception as e:
            raise DatabaseException(f"Database query failed: {str(e)}", e)
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def execute_non_query(self, query: str, params: tuple = None) -> int:
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            result = cursor.execute(query, params or ())
            connection.commit()
            return result
        except Exception as e:
            if connection:
                connection.rollback()
            raise DatabaseException(f"Database operation failed: {str(e)}", e)
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def fetch_dataframe(self, query: str, params: tuple = None) -> pd.DataFrame:
        connection = None
        try:
            connection = self.get_connection()
            return pd.read_sql(query, connection, params=params)
        except Exception as e:
            raise DatabaseException(f"DataFrame fetch failed: {str(e)}", e)
        finally:
            if connection:
                connection.close()
    
    @abstractmethod
    def table_name(self) -> str:
        pass