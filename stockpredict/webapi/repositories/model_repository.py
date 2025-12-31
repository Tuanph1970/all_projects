from typing import Dict, List, Optional
from repositories.base_repository import BaseRepository
from core.exceptions import EntityNotFoundException


class ModelRepository(BaseRepository):
    def table_name(self) -> str:
        return "model_instances"
    
    def create_model(self, model_name: str, model_type: str, model_sub_type: str = None,
                    past_covariate: bool = False, future_covariate: bool = False, created_by: str = None) -> int:
        query = f"""
        INSERT INTO {self.table_name()}
        (model_name, model_type, model_sub_type, past_covariate, future_covariate, created_by, user_id, status, config_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'created', '{{}}')
        """
        params = (model_name, model_type, model_sub_type, past_covariate, future_covariate, created_by, created_by)
        
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
    
    def get_model_by_id(self, model_id: int) -> Optional[Dict]:
        query = f"SELECT * FROM {self.table_name()} WHERE id = %s"
        result = self.execute_query(query, (model_id,))
        if not result:
            raise EntityNotFoundException("Model", str(model_id))
        return result[0]
    
    def get_all_models(self) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()} ORDER BY id DESC"
        return self.execute_query(query)
    
    def update_model(self, model_id: int, model_name: str = None, model_type: str = None,
                    model_sub_type: str = None) -> bool:
        update_fields = []
        params = []
        
        if model_name:
            update_fields.append("model_name = %s")
            params.append(model_name)
        
        if model_type:
            update_fields.append("model_type = %s")
            params.append(model_type)
        
        if model_sub_type:
            update_fields.append("model_sub_type = %s")
            params.append(model_sub_type)
        
        if not update_fields:
            return False
        
        params.append(model_id)
        query = f"UPDATE {self.table_name()} SET {', '.join(update_fields)} WHERE id = %s"
        
        return self.execute_non_query(query, tuple(params)) > 0
    
    def delete_model(self, model_id: int) -> bool:
        query = f"DELETE FROM {self.table_name()} WHERE id = %s"
        return self.execute_non_query(query, (model_id,)) > 0
    
    def get_models_by_type(self, model_type: str) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()} WHERE model_type = %s ORDER BY id DESC"
        return self.execute_query(query, (model_type,))

    def get_models_by_user(self, user_id: str) -> List[Dict]:
        """Get all models created by a specific user"""
        query = f"SELECT * FROM {self.table_name()} WHERE user_id = %s ORDER BY id DESC"
        return self.execute_query(query, (user_id,))


class ModelParameterRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_model_parameters"
    
    def save_model_parameters(self, model_id: int, parameters: Dict) -> bool:
        for param_name, param_value in parameters.items():
            query = f"""
            INSERT INTO {self.table_name()} (model_id, parameter_name, parameter_value) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE parameter_value = VALUES(parameter_value)
            """
            self.execute_non_query(query, (model_id, param_name, str(param_value)))
        return True
    
    def get_model_parameters(self, model_id: int) -> Dict:
        query = f"SELECT parameter_name, parameter_value FROM {self.table_name()} WHERE model_id = %s"
        result = self.execute_query(query, (model_id,))
        return {row['parameter_name']: row['parameter_value'] for row in result}
    
    def delete_model_parameters(self, model_id: int) -> bool:
        query = f"DELETE FROM {self.table_name()} WHERE model_id = %s"
        return self.execute_non_query(query, (model_id,)) >= 0