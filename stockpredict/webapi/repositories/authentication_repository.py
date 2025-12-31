from typing import Dict, List, Optional
from repositories.base_repository import BaseRepository
from core.exceptions import EntityNotFoundException


class AuthenticationRepository(BaseRepository):
    def table_name(self) -> str:
        return "users"
    
    def login(self, user_email: str, password: str) -> Dict:
        query = f"SELECT id FROM {self.table_name()} WHERE email = %s AND password_hash = %s"
        result = self.execute_query(query, (user_email, password))
        
        if result:
            return {"id": result[0]["id"]}
        else:
            return {"id": -1}
    
    def get_user_info(self, user_id: int) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()} WHERE id = %s"
        return self.execute_query(query, (user_id,))
    
    def sign_up_new_user(self, user_name: str, email: str, password:str) -> bool:
        try:
            query = f"INSERT INTO {self.table_name()} (username, email,password_hash) VALUES (%s, %s ,%s)"
            return self.execute_non_query(query, (user_name, email,password)) > 0
        except Exception:
            return False
    
    def change_password(self, user_name: str, old_pass: str, new_pass: str) -> bool:
        try:
            query = f"UPDATE {self.table_name()} SET password_hash = %s WHERE username = %s AND password_hash = %s"
            return self.execute_non_query(query, (new_pass, user_name, old_pass)) > 0
        except Exception:
            return False
    
    def reset_password(self, user_email: str, new_password: str = None) -> bool:
        try:

            query = f"UPDATE {self.table_name()} SET password_hash = %s WHERE email = %s"
            return self.execute_non_query(query, (new_password, user_email)) > 0
        except Exception:
            return False