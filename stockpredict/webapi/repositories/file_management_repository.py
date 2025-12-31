from typing import Dict, List, Optional
from repositories.base_repository import BaseRepository


class FileUploadRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_upload_file"
    
    def insert_file(self, file_name: str, owner_id: int = 0) -> bool:
        query = f"INSERT INTO {self.table_name()} (file_name, file_status, owner_id) VALUES (%s, %s, %s)"
        return self.execute_non_query(query, (file_name, 0, owner_id)) > 0
    
    def get_upload_files(self) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()}"
        return self.execute_query(query)
    
    def get_file_name_by_id(self, file_id: int) -> Optional[str]:
        query = f"SELECT file_name FROM {self.table_name()} WHERE id = %s"
        result = self.execute_query(query, (file_id,))
        return result[0]["file_name"] if result else None
    
    def delete_file(self, file_id: int) -> bool:
        query = f"UPDATE {self.table_name()} SET file_status = 2 WHERE id = %s"
        return self.execute_non_query(query, (file_id,)) > 0
    
    def mark_process_file(self, file_id: int) -> bool:
        query = f"UPDATE {self.table_name()} SET file_status = 1 WHERE id = %s"
        return self.execute_non_query(query, (file_id,)) > 0