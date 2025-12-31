from typing import Dict, List
from repositories.base_repository import BaseRepository


class AgentRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_agent"
    
    def get_all_agents(self) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()}"
        return self.execute_query(query)