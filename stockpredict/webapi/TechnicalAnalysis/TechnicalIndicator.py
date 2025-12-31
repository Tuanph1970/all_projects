import mysql.connector as connection
import  pandas as pd
# import pandas_ta as ta  # Temporarily disabled - replaced with ta library
import ta as ta_lib  # Using ta library instead
import json
from datetime import datetime

class TechnicalIndicator:
    def __init__(self):
        pass
    def getMACD(self,ticker,fast=12,slow=26,signal=9,start=None,end=None):
        from services.stock_market_service import CompanyService
        df = CompanyService.get_price_history_df(ticker,"VCI",start=start,end=end)

        # Using ta library instead of pandas_ta
        macd_indicator = ta_lib.trend.MACD(df['close'], window_fast=fast, window_slow=slow)
        df['MACD'] = macd_indicator.macd()
        df['Signal'] = macd_indicator.macd_signal()
        df['Histogram'] = macd_indicator.macd_diff()

        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
        df = df[df['time'].dt.date >= start_date]
        df = df[df['time'].dt.date <= end_date]

        jsonvalues = json.loads(df.reset_index().to_json(orient='records'))
        return jsonvalues
    def getRSI(self,ticker,length=14,start=None,end=None):
        from services.stock_market_service import CompanyService
        df = CompanyService.get_price_history_df(ticker, "VCI", start=start, end=end)

        # Using ta library instead of pandas_ta
        df['RSI'] = ta_lib.momentum.RSIIndicator(df['close'], window=length).rsi()
        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
        df = df[df['time'].dt.date >= start_date]
        df = df[df['time'].dt.date <= end_date]
        jsonvalues = json.loads(df.reset_index().to_json(orient='records'))
        return jsonvalues
    def getParabolicSARIndicator(self,ticker,start=None,end=None):
        from services.stock_market_service import CompanyService
        df = CompanyService.get_price_history_df(ticker, "VCI", start=start, end=end)

        # Using ta library instead of pandas_ta
        df['PSAR'] = ta_lib.trend.PSARIndicator(df['high'], df['low'], df['close']).psar()

        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
        df = df[df['time'].dt.date >= start_date]
        df = df[df['time'].dt.date <= end_date]

        jsonvalues = json.loads(df.reset_index().to_json(orient='records'))
        return jsonvalues


    def getSMA(self,ticker,length=25,start=None,end=None):
        from services.stock_market_service import CompanyService
        df = CompanyService.get_price_history_df(ticker, "VCI", start=start, end=end)

        # Using ta library instead of pandas_ta
        df['SMA'] = ta_lib.trend.SMAIndicator(df['close'], window=length).sma_indicator()

        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
        df = df[df['time'].dt.date >= start_date]
        df = df[df['time'].dt.date <= end_date]

        jsonvalues = json.loads(df.reset_index().to_json(orient='records'))
        return jsonvalues


    def getEMA(self,ticker,length=12,start=None,end = None):
        from services.stock_market_service import CompanyService
        df = CompanyService.get_price_history_df(ticker, "VCI", start=start, end=end)

        # Using ta library instead of pandas_ta
        df['EMA'] = ta_lib.trend.EMAIndicator(df['close'], window=length).ema_indicator()

        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
        df = df[df['time'].dt.date >= start_date]
        df = df[df['time'].dt.date <= end_date]

        jsonvalues = json.loads(df.reset_index().to_json(orient='records'))
        return jsonvalues











