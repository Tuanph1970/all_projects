from typing import Dict, List, Optional
from datetime import datetime
from repositories.time_series_repository import TimeSeriesRepository, SeriesTypeRepository
from core.exceptions import EntityNotFoundException, TimeSeriesException
from core.decorators import validate_input


class TimeSeriesService:
    def __init__(self):
        self.time_series_repo = TimeSeriesRepository()
        self.series_type_repo = SeriesTypeRepository()
    
    @validate_input()
    def add_time_series(self, data: Dict) -> bool:
        try:
            return self.time_series_repo.add_time_series(data)
        except Exception as e:
            raise TimeSeriesException(f"Failed to add time series: {str(e)}")
    
    @validate_input()
    def modify_time_series(self, data: Dict) -> bool:
        try:
            return self.time_series_repo.modify_time_series(data)
        except Exception as e:
            raise TimeSeriesException(f"Failed to modify time series: {str(e)}")
    
    def get_all_time_series(self) -> List[Dict]:
        try:
            return self.time_series_repo.get_all_time_series()
        except Exception as e:
            raise TimeSeriesException(f"Failed to retrieve time series: {str(e)}")
    
    def get_series_by_id(self, series_id: int) -> Optional[Dict]:
        try:
            return self.time_series_repo.get_series_by_id(series_id)
        except Exception as e:
            raise TimeSeriesException(f"Failed to get time series {series_id}: {str(e)}")
    
    def delete_series_by_id(self, series_id: int) -> Dict:
        try:
            result = self.time_series_repo.delete_series_by_id(series_id)
            if result == 0:
                return {"status": "success", "message": "Time series deleted successfully"}
            else:
                return {"status": "error", "message": "Cannot delete time series - it is referenced by solutions"}
        except Exception as e:
            raise TimeSeriesException(f"Failed to delete time series {series_id}: {str(e)}")
    
    def get_series_by_ids(self, time_series_ids: List[int]) -> List[Dict]:
        try:
            return self.time_series_repo.get_series_by_ids(time_series_ids)
        except Exception as e:
            raise TimeSeriesException(f"Failed to get time series by IDs: {str(e)}")
    
    @validate_input()
    def update_series_batch(self, series_data: List[Dict]) -> bool:
        try:
            return self.time_series_repo.update_series_batch(series_data)
        except Exception as e:
            raise TimeSeriesException(f"Failed to update time series batch: {str(e)}")
    
    def get_series_types(self) -> List[Dict]:
        try:
            return self.series_type_repo.get_series_types()
        except Exception as e:
            raise TimeSeriesException(f"Failed to get series types: {str(e)}")
    
    def create_time_series(self, series_name: str, indicator_id: int,
                          end_date: str = None, created_by: int = 0, status: int = 1) -> bool:
        data = {
            'series_name': series_name,
            'indicator_id': indicator_id,
            'end_date': end_date,
            'status': status,
            'created_date': datetime.now(),
            'created_by': created_by
        }
        return self.add_time_series(data)
    
    def update_time_series(self, series_id: int, series_name: str = None,
                          indicator_id: int = None, end_date: str = None) -> bool:
        data = {'id': series_id}

        if series_name:
            data['series_name'] = series_name
        if indicator_id:
            data['indicator_id'] = indicator_id
        if end_date:
            data['end_date'] = end_date

        data['updated_date'] = datetime.now()

        return self.modify_time_series(data)
    
    def validate_time_series_data(self, data: Dict) -> bool:
        required_fields = ['series_name', 'indicator_id']
        for field in required_fields:
            if field not in data:
                raise TimeSeriesException(f"Missing required field: {field}")

        # Validate indicator exists
        # Note: You may want to add a method to validate indicator_id against tbl_technical_indicators
        # For now, we'll rely on the foreign key constraint in the database

        return True