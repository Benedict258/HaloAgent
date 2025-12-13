from datetime import datetime
from typing import Dict, List, Optional
from pyairtable import Api
from app.core.config import settings

class AirtableService:
    def __init__(self):
        self.api_key = settings.AIRTABLE_API_KEY
        self.base_id = settings.AIRTABLE_BASE_ID
        self.api = Api(self.api_key) if self.api_key else None
        
    def get_table(self, table_name: str):
        if not self.api or not self.base_id:
            return None
        return self.api.table(self.base_id, table_name)
    
    async def create_record(self, table_name: str, data: Dict) -> Optional[Dict]:
        """Create a record in Airtable"""
        table = self.get_table(table_name)
        if not table:
            return None
        return table.create(data)

    async def get_records(self, table_name: str, formula: Optional[str] = None) -> List[Dict]:
        """Get records from Airtable"""
        table = self.get_table(table_name)
        if not table:
            return []
        if formula:
            return table.all(formula=formula)
        return table.all()

airtable_service = AirtableService()
