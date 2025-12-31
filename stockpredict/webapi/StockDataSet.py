import mysql.connector as connection
import pandas as pd
from datetime import datetime
import darts
from services.stock_entity_service import MarketStockEntity
from darts import TimeSeries
from darts.dataprocessing.transformers import Scaler
from services.stock_market_service import CompanyService
class StockTimeSeries:
    def __init__(self,fieldName,timeSeries):
        self.scaler = Scaler()
        self.field_name = fieldName
        self.time_series = timeSeries
        self.time_series = darts.utils.missing_values.fill_missing_values(self.time_series, fill='auto', inplace=True)
    def get_scaler(self):
        return self.scaler

    def get_series(self):
        return self.time_series



class StockDataSet:
    def __init__(self,ticker):
        self.stock_time_series = []
        self.ticker = ticker
        company_service = CompanyService()
        self.data_frame = company_service.get_price_history_df(symbol=ticker,source="VCI")
    def add_field(self,field_name,start_time,stop_time):
        field_name = field_name.lower()
        start_time = datetime.strptime(start_time,"%Y-%m-%d")
        end_time = datetime.strptime(stop_time, "%Y-%m-%d")
        df = self.data_frame[['time', field_name]]
        df = df[(df['time'] >= start_time) & (df['time'] <= end_time) ]
        df = df.drop_duplicates(subset=['time'],keep='first')
        series = TimeSeries.from_dataframe(df, time_col='time', value_cols=field_name, freq='B')
        stock_series = StockTimeSeries(field_name,series)
        self.stock_time_series.append(stock_series)

    def add_field_from_dataframe(self, field_name, df):
        """
        Add a field from a pre-calculated dataframe (e.g., technical indicators)

        Args:
            field_name: Name of the field/indicator
            df: DataFrame with 'date' and the field_name columns
        """
        # Ensure the dataframe has the required columns
        if 'date' not in df.columns or field_name not in df.columns:
            raise ValueError(f"DataFrame must contain 'date' and '{field_name}' columns")

        # Make a copy and prepare the dataframe
        df_copy = df[['date', field_name]].copy()
        df_copy = df_copy.dropna()  # Remove any NaN values
        df_copy = df_copy.drop_duplicates(subset=['date'], keep='first')

        # Convert date column to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(df_copy['date']):
            df_copy['date'] = pd.to_datetime(df_copy['date'])

        # Create TimeSeries from the dataframe
        series = TimeSeries.from_dataframe(df_copy, time_col='date', value_cols=field_name, freq='B')

        # Create and add StockTimeSeries object
        stock_series = StockTimeSeries(field_name, series)
        self.stock_time_series.append(stock_series)

    def get_stock_time_series(self,field_name):
        match_obj = next(x for x in self.stock_time_series if x.field_name == field_name)
        return match_obj
