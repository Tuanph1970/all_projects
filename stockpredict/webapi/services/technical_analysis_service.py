from typing import Dict, List
import json
from TechnicalAnalysis.TechnicalIndicator import TechnicalIndicator
from services.stock_market_service import CompanyService
from core.exceptions import ExternalServiceException


class TechnicalAnalysisService:
    def __init__(self):
        self.indicator = TechnicalIndicator()
        self.company_service = CompanyService()
    
    def get_macd(self, ticker: str, fast: int, slow: int, signal: int, 
                start: str, end: str) -> List[Dict]:
        try:
            return self.indicator.getMACD(
                ticker=ticker, fast=fast, slow=slow, 
                signal=signal, start=start, end=end
            )
        except Exception as e:
            raise ExternalServiceException("TechnicalIndicator", f"MACD calculation failed: {str(e)}")
    
    def get_sma(self, ticker: str, length: int, start: str, end: str) -> List[Dict]:
        try:
            return self.indicator.getSMA(
                ticker=ticker, length=length, start=start, end=end
            )
        except Exception as e:
            raise ExternalServiceException("TechnicalIndicator", f"SMA calculation failed: {str(e)}")
    
    def get_ema(self, ticker: str, length: int, start: str, end: str) -> List[Dict]:
        try:
            return self.indicator.getEMA(
                ticker=ticker, length=length, start=start, end=end
            )
        except Exception as e:
            raise ExternalServiceException("TechnicalIndicator", f"EMA calculation failed: {str(e)}")
    
    def get_rsi(self, ticker: str, length: int, start: str, end: str) -> List[Dict]:
        try:
            return self.indicator.getRSI(
                ticker=ticker, length=length, start=start, end=end
            )
        except Exception as e:
            raise ExternalServiceException("TechnicalIndicator", f"RSI calculation failed: {str(e)}")
    
    def get_parabolic_sar(self, ticker: str, start: str, end: str) -> List[Dict]:
        try:
            return self.indicator.getParabolicSARIndicator(
                ticker=ticker, start=start, end=end
            )
        except Exception as e:
            raise ExternalServiceException("TechnicalIndicator", f"PSAR calculation failed: {str(e)}")
    
    def get_candlestick_data(self, ticker: str, start: str, end: str) -> List[Dict]:
        try:
            df = self.company_service.get_price_history_df(ticker, "VCI", start=start, end=end)
            df = df[['time', 'open', 'high', 'low', 'close']]
            json_str = df.to_json(orient='records', force_ascii=False, date_format='iso')
            return json.loads(json_str)
        except Exception as e:
            raise ExternalServiceException("CompanyService", f"Candlestick data fetch failed: {str(e)}")
    
    def get_volume_data(self, ticker: str, start: str, end: str) -> List[Dict]:
        try:
            df = self.company_service.get_price_history_df(ticker, "VCI", start=start, end=end)
            df_ret = df[['time', 'volume']]
            json_str = df_ret.to_json(orient='records', force_ascii=False, date_format='iso')
            return json.loads(json_str)
        except Exception as e:
            raise ExternalServiceException("CompanyService", f"Volume data fetch failed: {str(e)}")