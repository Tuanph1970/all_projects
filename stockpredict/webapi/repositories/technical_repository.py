from typing import Dict, List
from repositories.base_repository import BaseRepository


class TechnicalRepository(BaseRepository):
    def table_name(self) -> str:
        return "technical_indicator"
    
    def get_technical_indicators_by_group_name(self, group_name: str) -> List[Dict]:
        query = f"SELECT indicator_id, indicator_name FROM {self.table_name()} WHERE group_name = %s"
        return self.execute_query(query, (group_name,))
    
    def get_technical_indicator_params(self) -> List[Dict]:
        query = "SELECT * FROM tbl_indicator_params"
        return self.execute_query(query)