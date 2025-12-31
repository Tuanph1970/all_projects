"""
Advanced Technical Indicators Service
Provides comprehensive technical analysis indicators for AI-driven stock analysis.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import ta
from scipy import stats
from services.stock_entities import StockService
from core.exceptions import ExternalServiceException

class IndicatorCategory(Enum):
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    SUPPORT_RESISTANCE = "support_resistance"
    PRICE_TRANSFORM = "price_transform"
    BILL_WILLIAMS = "bill_williams"

@dataclass
class IndicatorConfig:
    name: str
    category: IndicatorCategory
    description: str
    parameters: Dict
    calculation_func: str

class AdvancedTechnicalIndicators:
    def __init__(self):
        self.stock_service = StockService()
        self.indicators_config = self._initialize_indicators_config()

    def _initialize_indicators_config(self) -> Dict[str, IndicatorConfig]:
        """Initialize configuration for all supported indicators"""
        return {
            # ============================================================
            # TREND INDICATORS - Moving Averages
            # ============================================================
            'SMA': IndicatorConfig(
                name='SMA',
                category=IndicatorCategory.TREND,
                description='Simple Moving Average',
                parameters={'period': 20},
                calculation_func='calculate_sma'
            ),
            'EMA': IndicatorConfig(
                name='EMA',
                category=IndicatorCategory.TREND,
                description='Exponential Moving Average',
                parameters={'period': 20},
                calculation_func='calculate_ema'
            ),
            'WMA': IndicatorConfig(
                name='WMA',
                category=IndicatorCategory.TREND,
                description='Weighted Moving Average',
                parameters={'period': 20},
                calculation_func='calculate_wma'
            ),
            'DEMA': IndicatorConfig(
                name='DEMA',
                category=IndicatorCategory.TREND,
                description='Double Exponential Moving Average',
                parameters={'period': 20},
                calculation_func='calculate_dema'
            ),
            'TEMA': IndicatorConfig(
                name='TEMA',
                category=IndicatorCategory.TREND,
                description='Triple Exponential Moving Average',
                parameters={'period': 20},
                calculation_func='calculate_tema'
            ),

            # TREND INDICATORS - Trend Direction
            'MACD': IndicatorConfig(
                name='MACD',
                category=IndicatorCategory.TREND,
                description='Moving Average Convergence Divergence',
                parameters={'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
                calculation_func='calculate_macd'
            ),
            'ADX': IndicatorConfig(
                name='ADX',
                category=IndicatorCategory.TREND,
                description='Average Directional Index',
                parameters={'period': 14},
                calculation_func='calculate_adx'
            ),
            'PSAR': IndicatorConfig(
                name='PSAR',
                category=IndicatorCategory.TREND,
                description='Parabolic SAR',
                parameters={'step': 0.02, 'max_step': 0.2},
                calculation_func='calculate_psar'
            ),
            'SUPERTREND': IndicatorConfig(
                name='SUPERTREND',
                category=IndicatorCategory.TREND,
                description='Supertrend Indicator',
                parameters={'period': 10, 'multiplier': 3},
                calculation_func='calculate_supertrend'
            ),
            'ICHIMOKU': IndicatorConfig(
                name='ICHIMOKU',
                category=IndicatorCategory.TREND,
                description='Ichimoku Cloud',
                parameters={'tenkan_period': 9, 'kijun_period': 26, 'senkou_b_period': 52},
                calculation_func='calculate_ichimoku'
            ),
            'AROON': IndicatorConfig(
                name='AROON',
                category=IndicatorCategory.TREND,
                description='Aroon Indicator',
                parameters={'period': 25},
                calculation_func='calculate_aroon'
            ),
            'VORTEX': IndicatorConfig(
                name='VORTEX',
                category=IndicatorCategory.TREND,
                description='Vortex Indicator',
                parameters={'period': 14},
                calculation_func='calculate_vortex'
            ),

            # ============================================================
            # MOMENTUM INDICATORS
            # ============================================================
            'RSI': IndicatorConfig(
                name='RSI',
                category=IndicatorCategory.MOMENTUM,
                description='Relative Strength Index',
                parameters={'period': 14},
                calculation_func='calculate_rsi'
            ),
            'STOCH': IndicatorConfig(
                name='STOCH',
                category=IndicatorCategory.MOMENTUM,
                description='Stochastic Oscillator',
                parameters={'k_period': 14, 'd_period': 3},
                calculation_func='calculate_stochastic'
            ),
            'STOCH_RSI': IndicatorConfig(
                name='STOCH_RSI',
                category=IndicatorCategory.MOMENTUM,
                description='Stochastic RSI',
                parameters={'period': 14, 'smooth_k': 3, 'smooth_d': 3},
                calculation_func='calculate_stochastic_rsi'
            ),
            'CCI': IndicatorConfig(
                name='CCI',
                category=IndicatorCategory.MOMENTUM,
                description='Commodity Channel Index',
                parameters={'period': 20},
                calculation_func='calculate_cci'
            ),
            'WILLIAMS_R': IndicatorConfig(
                name='WILLIAMS_R',
                category=IndicatorCategory.MOMENTUM,
                description='Williams %R',
                parameters={'period': 14},
                calculation_func='calculate_williams_r'
            ),
            'ROC': IndicatorConfig(
                name='ROC',
                category=IndicatorCategory.MOMENTUM,
                description='Rate of Change',
                parameters={'period': 12},
                calculation_func='calculate_roc'
            ),
            'MOM': IndicatorConfig(
                name='MOM',
                category=IndicatorCategory.MOMENTUM,
                description='Momentum Indicator',
                parameters={'period': 10},
                calculation_func='calculate_momentum'
            ),
            'TSI': IndicatorConfig(
                name='TSI',
                category=IndicatorCategory.MOMENTUM,
                description='True Strength Index',
                parameters={'long_period': 25, 'short_period': 13, 'signal_period': 13},
                calculation_func='calculate_tsi'
            ),
            'UO': IndicatorConfig(
                name='UO',
                category=IndicatorCategory.MOMENTUM,
                description='Ultimate Oscillator',
                parameters={'short_period': 7, 'medium_period': 14, 'long_period': 28},
                calculation_func='calculate_ultimate_oscillator'
            ),
            'AO': IndicatorConfig(
                name='AO',
                category=IndicatorCategory.MOMENTUM,
                description='Awesome Oscillator',
                parameters={'fast_period': 5, 'slow_period': 34},
                calculation_func='calculate_awesome_oscillator'
            ),

            # ============================================================
            # VOLATILITY INDICATORS
            # ============================================================
            'BB': IndicatorConfig(
                name='BB',
                category=IndicatorCategory.VOLATILITY,
                description='Bollinger Bands',
                parameters={'period': 20, 'std': 2},
                calculation_func='calculate_bollinger_bands'
            ),
            'ATR': IndicatorConfig(
                name='ATR',
                category=IndicatorCategory.VOLATILITY,
                description='Average True Range',
                parameters={'period': 14},
                calculation_func='calculate_atr'
            ),
            'KELTNER': IndicatorConfig(
                name='KELTNER',
                category=IndicatorCategory.VOLATILITY,
                description='Keltner Channel',
                parameters={'period': 20, 'multiplier': 2.0},
                calculation_func='calculate_keltner_channel'
            ),
            'DONCHIAN': IndicatorConfig(
                name='DONCHIAN',
                category=IndicatorCategory.VOLATILITY,
                description='Donchian Channel',
                parameters={'period': 20},
                calculation_func='calculate_donchian_channel'
            ),
            'STDDEV': IndicatorConfig(
                name='STDDEV',
                category=IndicatorCategory.VOLATILITY,
                description='Standard Deviation',
                parameters={'period': 20},
                calculation_func='calculate_std_dev'
            ),
            'HV': IndicatorConfig(
                name='HV',
                category=IndicatorCategory.VOLATILITY,
                description='Historical Volatility',
                parameters={'period': 20},
                calculation_func='calculate_historical_volatility'
            ),

            # ============================================================
            # VOLUME INDICATORS
            # ============================================================
            'VOLUME': IndicatorConfig(
                name='VOLUME',
                category=IndicatorCategory.VOLUME,
                description='Trading Volume',
                parameters={},
                calculation_func='calculate_volume'
            ),
            'OBV': IndicatorConfig(
                name='OBV',
                category=IndicatorCategory.VOLUME,
                description='On Balance Volume',
                parameters={},
                calculation_func='calculate_obv'
            ),
            'VWAP': IndicatorConfig(
                name='VWAP',
                category=IndicatorCategory.VOLUME,
                description='Volume Weighted Average Price',
                parameters={},
                calculation_func='calculate_vwap'
            ),
            'MFI': IndicatorConfig(
                name='MFI',
                category=IndicatorCategory.VOLUME,
                description='Money Flow Index',
                parameters={'period': 14},
                calculation_func='calculate_mfi'
            ),
            'AD': IndicatorConfig(
                name='AD',
                category=IndicatorCategory.VOLUME,
                description='Accumulation/Distribution Line',
                parameters={},
                calculation_func='calculate_ad'
            ),
            'CMF': IndicatorConfig(
                name='CMF',
                category=IndicatorCategory.VOLUME,
                description='Chaikin Money Flow',
                parameters={'period': 20},
                calculation_func='calculate_cmf'
            ),
            'CHO': IndicatorConfig(
                name='CHO',
                category=IndicatorCategory.VOLUME,
                description='Chaikin Oscillator',
                parameters={'fast_period': 3, 'slow_period': 10},
                calculation_func='calculate_chaikin_oscillator'
            ),
            'VOSC': IndicatorConfig(
                name='VOSC',
                category=IndicatorCategory.VOLUME,
                description='Volume Oscillator',
                parameters={'fast_period': 5, 'slow_period': 10},
                calculation_func='calculate_volume_oscillator'
            ),
            'EOM': IndicatorConfig(
                name='EOM',
                category=IndicatorCategory.VOLUME,
                description='Ease of Movement',
                parameters={'period': 14},
                calculation_func='calculate_eom'
            ),
            'FI': IndicatorConfig(
                name='FI',
                category=IndicatorCategory.VOLUME,
                description='Force Index',
                parameters={'period': 13},
                calculation_func='calculate_force_index'
            ),
            'NVI': IndicatorConfig(
                name='NVI',
                category=IndicatorCategory.VOLUME,
                description='Negative Volume Index',
                parameters={},
                calculation_func='calculate_nvi'
            ),
            'PVI': IndicatorConfig(
                name='PVI',
                category=IndicatorCategory.VOLUME,
                description='Positive Volume Index',
                parameters={},
                calculation_func='calculate_pvi'
            ),
            'Volume_MA': IndicatorConfig(
                name='Volume_MA',
                category=IndicatorCategory.VOLUME,
                description='Volume Moving Average',
                parameters={'period': 20},
                calculation_func='calculate_volume_ma'
            ),

            # ============================================================
            # SUPPORT & RESISTANCE INDICATORS
            # ============================================================
            'PIVOT': IndicatorConfig(
                name='PIVOT',
                category=IndicatorCategory.SUPPORT_RESISTANCE,
                description='Pivot Points',
                parameters={'type': 'standard'},
                calculation_func='calculate_pivot_points'
            ),
            'FIB_RET': IndicatorConfig(
                name='FIB_RET',
                category=IndicatorCategory.SUPPORT_RESISTANCE,
                description='Fibonacci Retracement',
                parameters={},
                calculation_func='calculate_fibonacci_retracement'
            ),
            'FIB_EXT': IndicatorConfig(
                name='FIB_EXT',
                category=IndicatorCategory.SUPPORT_RESISTANCE,
                description='Fibonacci Extension',
                parameters={},
                calculation_func='calculate_fibonacci_extension'
            ),

            # ============================================================
            # PRICE TRANSFORM INDICATORS
            # ============================================================
            'HEIKIN_ASHI': IndicatorConfig(
                name='HEIKIN_ASHI',
                category=IndicatorCategory.PRICE_TRANSFORM,
                description='Heikin Ashi Candles',
                parameters={},
                calculation_func='calculate_heikin_ashi'
            ),
            'RENKO': IndicatorConfig(
                name='RENKO',
                category=IndicatorCategory.PRICE_TRANSFORM,
                description='Renko Chart',
                parameters={'box_size': 1},
                calculation_func='calculate_renko'
            ),
            'TP': IndicatorConfig(
                name='TP',
                category=IndicatorCategory.PRICE_TRANSFORM,
                description='Typical Price',
                parameters={},
                calculation_func='calculate_typical_price'
            ),
            'MP': IndicatorConfig(
                name='MP',
                category=IndicatorCategory.PRICE_TRANSFORM,
                description='Median Price',
                parameters={},
                calculation_func='calculate_median_price'
            ),
            'WC': IndicatorConfig(
                name='WC',
                category=IndicatorCategory.PRICE_TRANSFORM,
                description='Weighted Close',
                parameters={},
                calculation_func='calculate_weighted_close'
            ),

            # ============================================================
            # BILL WILLIAMS INDICATORS
            # ============================================================
            'ALLIGATOR': IndicatorConfig(
                name='ALLIGATOR',
                category=IndicatorCategory.BILL_WILLIAMS,
                description='Williams Alligator',
                parameters={'jaw_period': 13, 'teeth_period': 8, 'lips_period': 5},
                calculation_func='calculate_alligator'
            ),
            'FRACTALS': IndicatorConfig(
                name='FRACTALS',
                category=IndicatorCategory.BILL_WILLIAMS,
                description='Williams Fractals',
                parameters={},
                calculation_func='calculate_fractals'
            ),
            'GATOR': IndicatorConfig(
                name='GATOR',
                category=IndicatorCategory.BILL_WILLIAMS,
                description='Gator Oscillator',
                parameters={'jaw_period': 13, 'teeth_period': 8, 'lips_period': 5},
                calculation_func='calculate_gator_oscillator'
            ),
            'MFI_BW': IndicatorConfig(
                name='MFI_BW',
                category=IndicatorCategory.BILL_WILLIAMS,
                description='Market Facilitation Index (Bill Williams)',
                parameters={},
                calculation_func='calculate_mfi_bw'
            ),
            'AC': IndicatorConfig(
                name='AC',
                category=IndicatorCategory.BILL_WILLIAMS,
                description='Accelerator Oscillator',
                parameters={'fast_period': 5, 'slow_period': 34},
                calculation_func='calculate_accelerator_oscillator'
            ),
        }

    def get_price_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get stock price data and prepare for technical analysis"""
        try:
            df = self.stock_service.get_price_history(
                symbol=symbol,
                start=start_date,
                end=end_date
            )

            if df.empty:
                raise ValueError(f"No data found for symbol {symbol}")

            # Ensure proper column names
            if 'time' not in df.columns:
                df = df.reset_index()

            df['date'] = pd.to_datetime(df['time'])
            df = df.set_index('date')

            return df[['open', 'high', 'low', 'close', 'volume']].copy()

        except Exception as e:
            raise ExternalServiceException("StockService", f"Failed to get price data: {str(e)}")

    def calculate_indicator(self, symbol: str, indicator_name: str,
                          start_date: str, end_date: str,
                          custom_params: Optional[Dict] = None) -> Dict:
        """Calculate a specific technical indicator"""
        if indicator_name not in self.indicators_config:
            raise ValueError(f"Unsupported indicator: {indicator_name}")

        config = self.indicators_config[indicator_name]
        df = self.get_price_data(symbol, start_date, end_date)

        # Merge custom parameters with default ones
        params = config.parameters.copy()
        if custom_params:
            params.update(custom_params)

        # Call the appropriate calculation function
        calc_func = getattr(self, config.calculation_func)
        result = calc_func(df, **params)

        return {
            'indicator': indicator_name,
            'category': config.category.value,
            'description': config.description,
            'data': result,
            'parameters': params
        }

    def calculate_multiple_indicators(self, symbol: str, indicators: List[str],
                                    start_date: str, end_date: str,
                                    custom_params: Optional[Dict[str, Dict]] = None) -> Dict:
        """Calculate multiple indicators at once"""
        results = {}
        df = self.get_price_data(symbol, start_date, end_date)

        for indicator in indicators:
            if indicator not in self.indicators_config:
                continue

            config = self.indicators_config[indicator]
            params = config.parameters.copy()

            if custom_params and indicator in custom_params:
                params.update(custom_params[indicator])

            try:
                calc_func = getattr(self, config.calculation_func)
                result = calc_func(df, **params)

                results[indicator] = {
                    'category': config.category.value,
                    'description': config.description,
                    'data': result,
                    'parameters': params
                }
            except Exception as e:
                results[indicator] = {'error': str(e)}

        return results

    # Trend Indicators
    def calculate_macd(self, df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> List[Dict]:
        """Calculate MACD"""
        macd_line = ta.trend.MACD(df['close'], window_fast=fast_period, window_slow=slow_period, window_sign=signal_period).macd()
        signal_line = ta.trend.MACD(df['close'], window_fast=fast_period, window_slow=slow_period, window_sign=signal_period).macd_signal()
        histogram = ta.trend.MACD(df['close'], window_fast=fast_period, window_slow=slow_period, window_sign=signal_period).macd_diff()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'macd': macd_line.iloc[i] if not pd.isna(macd_line.iloc[i]) else None,
                'signal': signal_line.iloc[i] if not pd.isna(signal_line.iloc[i]) else None,
                'histogram': histogram.iloc[i] if not pd.isna(histogram.iloc[i]) else None
            })

        return result

    def calculate_sma(self, df: pd.DataFrame, period: int = 20) -> List[Dict]:
        """Calculate Simple Moving Average"""
        sma = ta.trend.SMAIndicator(df['close'], window=period).sma_indicator()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'sma': sma.iloc[i] if not pd.isna(sma.iloc[i]) else None
            })

        return result

    def calculate_ema(self, df: pd.DataFrame, period: int = 20) -> List[Dict]:
        """Calculate Exponential Moving Average"""
        ema = ta.trend.EMAIndicator(df['close'], window=period).ema_indicator()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'ema': ema.iloc[i] if not pd.isna(ema.iloc[i]) else None
            })

        return result

    def calculate_wma(self, df: pd.DataFrame, period: int = 20) -> List[Dict]:
        """Calculate Weighted Moving Average

        WMA gives more weight to recent prices.
        Formula: WMA = (P1*n + P2*(n-1) + ... + Pn*1) / (n + (n-1) + ... + 1)
        where n is the period and P1 is the most recent price
        """
        wma = ta.trend.WMAIndicator(df['close'], window=period).wma()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'wma': wma.iloc[i] if not pd.isna(wma.iloc[i]) else None
            })

        return result

    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> List[Dict]:
        """Calculate Average Directional Index"""
        adx = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=period)

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'adx': adx.adx().iloc[i] if not pd.isna(adx.adx().iloc[i]) else None,
                'adx_pos': adx.adx_pos().iloc[i] if not pd.isna(adx.adx_pos().iloc[i]) else None,
                'adx_neg': adx.adx_neg().iloc[i] if not pd.isna(adx.adx_neg().iloc[i]) else None
            })

        return result

    def calculate_psar(self, df: pd.DataFrame, step: float = 0.02, max_step: float = 0.2) -> List[Dict]:
        """Calculate Parabolic SAR"""
        psar = ta.trend.PSARIndicator(df['high'], df['low'], df['close'],
                                     step=step, max_step=max_step).psar()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'psar': psar.iloc[i] if not pd.isna(psar.iloc[i]) else None
            })

        return result

    # Momentum Indicators
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> List[Dict]:
        """Calculate Relative Strength Index"""
        rsi = ta.momentum.RSIIndicator(df['close'], window=period).rsi()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'rsi': rsi.iloc[i] if not pd.isna(rsi.iloc[i]) else None
            })

        return result

    def calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> List[Dict]:
        """Calculate Stochastic Oscillator"""
        stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'],
                                               window=k_period, smooth_window=d_period)

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'stoch_k': stoch.stoch().iloc[i] if not pd.isna(stoch.stoch().iloc[i]) else None,
                'stoch_d': stoch.stoch_signal().iloc[i] if not pd.isna(stoch.stoch_signal().iloc[i]) else None
            })

        return result

    def calculate_cci(self, df: pd.DataFrame, period: int = 20) -> List[Dict]:
        """Calculate Commodity Channel Index"""
        cci = ta.momentum.CCIIndicator(df['high'], df['low'], df['close'], window=period).cci()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'cci': cci.iloc[i] if not pd.isna(cci.iloc[i]) else None
            })

        return result

    def calculate_williams_r(self, df: pd.DataFrame, period: int = 14) -> List[Dict]:
        """Calculate Williams %R"""
        williams_r = ta.momentum.WilliamsRIndicator(df['high'], df['low'], df['close'],
                                                   lbp=period).williams_r()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'williams_r': williams_r.iloc[i] if not pd.isna(williams_r.iloc[i]) else None
            })

        return result

    def calculate_roc(self, df: pd.DataFrame, period: int = 12) -> List[Dict]:
        """Calculate Rate of Change"""
        roc = ta.momentum.ROCIndicator(df['close'], window=period).roc()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'roc': roc.iloc[i] if not pd.isna(roc.iloc[i]) else None
            })

        return result

    # Volatility Indicators
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std: int = 2, std_dev: int = None) -> List[Dict]:
        """Calculate Bollinger Bands

        Args:
            df: DataFrame with price data
            period: Window period for calculation (default: 20)
            std: Standard deviation multiplier (default: 2)
            std_dev: Alias for std parameter for backward compatibility
        """
        # Support both 'std' and 'std_dev' parameter names for backward compatibility
        std_value = std_dev if std_dev is not None else std
        bb = ta.volatility.BollingerBands(df['close'], window=period, window_dev=std_value)

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'bb_upper': bb.bollinger_hband().iloc[i] if not pd.isna(bb.bollinger_hband().iloc[i]) else None,
                'bb_middle': bb.bollinger_mavg().iloc[i] if not pd.isna(bb.bollinger_mavg().iloc[i]) else None,
                'bb_lower': bb.bollinger_lband().iloc[i] if not pd.isna(bb.bollinger_lband().iloc[i]) else None,
                'bb_width': bb.bollinger_wband().iloc[i] if not pd.isna(bb.bollinger_wband().iloc[i]) else None
            })

        return result

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> List[Dict]:
        """Calculate Average True Range"""
        atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'],
                                           window=period).average_true_range()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'atr': atr.iloc[i] if not pd.isna(atr.iloc[i]) else None
            })

        return result

    def calculate_keltner_channel(self, df: pd.DataFrame, period: int = 20, multiplier: float = 2.0) -> List[Dict]:
        """Calculate Keltner Channel"""
        kc = ta.volatility.KeltnerChannel(df['high'], df['low'], df['close'],
                                        window=period, window_atr=period)

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'kc_upper': kc.keltner_channel_hband().iloc[i] if not pd.isna(kc.keltner_channel_hband().iloc[i]) else None,
                'kc_middle': kc.keltner_channel_mband().iloc[i] if not pd.isna(kc.keltner_channel_mband().iloc[i]) else None,
                'kc_lower': kc.keltner_channel_lband().iloc[i] if not pd.isna(kc.keltner_channel_lband().iloc[i]) else None
            })

        return result

    def calculate_donchian_channel(self, df: pd.DataFrame, period: int = 20) -> List[Dict]:
        """Calculate Donchian Channel"""
        dc = ta.volatility.DonchianChannel(df['high'], df['low'], df['close'],
                                         window=period)

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'dc_upper': dc.donchian_channel_hband().iloc[i] if not pd.isna(dc.donchian_channel_hband().iloc[i]) else None,
                'dc_middle': dc.donchian_channel_mband().iloc[i] if not pd.isna(dc.donchian_channel_mband().iloc[i]) else None,
                'dc_lower': dc.donchian_channel_lband().iloc[i] if not pd.isna(dc.donchian_channel_lband().iloc[i]) else None
            })

        return result

    # Volume Indicators
    def calculate_obv(self, df: pd.DataFrame) -> List[Dict]:
        """Calculate On Balance Volume"""
        obv = ta.volume.OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'obv': obv.iloc[i] if not pd.isna(obv.iloc[i]) else None
            })

        return result

    def calculate_cmf(self, df: pd.DataFrame, period: int = 20) -> List[Dict]:
        """Calculate Chaikin Money Flow"""
        cmf = ta.volume.ChaikinMoneyFlowIndicator(df['high'], df['low'], df['close'],
                                                df['volume'], window=period).chaikin_money_flow()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'cmf': cmf.iloc[i] if not pd.isna(cmf.iloc[i]) else None
            })

        return result

    def calculate_vwap(self, df: pd.DataFrame, period: int = None, **kwargs) -> List[Dict]:
        """Calculate Volume Weighted Average Price

        Args:
            df: DataFrame with price data
            period: Window period (optional, for compatibility with Volume MA)
            **kwargs: Additional parameters for backward compatibility

        Note: VWAP is calculated as cumulative (price * volume) / cumulative volume.
        The period parameter is accepted for compatibility with Volume MA indicator
        but VWAP traditionally uses cumulative calculation from session start.
        """
        # Calculate VWAP using the standard formula
        # VWAP = cumulative(price * volume) / cumulative(volume)
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'vwap': vwap.iloc[i] if not pd.isna(vwap.iloc[i]) else None
            })

        return result

    def calculate_ad(self, df: pd.DataFrame) -> List[Dict]:
        """Calculate Accumulation/Distribution Line"""
        ad = ta.volume.AccDistIndexIndicator(df['high'], df['low'], df['close'],
                                           df['volume']).acc_dist_index()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'ad': ad.iloc[i] if not pd.isna(ad.iloc[i]) else None
            })

        return result

    def calculate_mfi(self, df: pd.DataFrame, period: int = 14) -> List[Dict]:
        """Calculate Money Flow Index"""
        mfi = ta.volume.MFIIndicator(df['high'], df['low'], df['close'],
                                   df['volume'], window=period).money_flow_index()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'mfi': mfi.iloc[i] if not pd.isna(mfi.iloc[i]) else None
            })

        return result

    def calculate_volume_ma(self, df: pd.DataFrame, period: int = 20) -> List[Dict]:
        """Calculate Volume Moving Average (Simple Moving Average of Volume)

        Args:
            df: DataFrame with volume data
            period: Window period for moving average (default: 20)

        Returns:
            List of dicts with date and volume_sma values
        """
        # Calculate simple moving average of volume
        volume_ma = df['volume'].rolling(window=period).mean()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'volume_sma': volume_ma.iloc[i] if not pd.isna(volume_ma.iloc[i]) else None
            })

        return result

    # ================================================================
    # NEW TREND INDICATORS
    # ================================================================

    def calculate_dema(self, df: pd.DataFrame, period: int = 20) -> List[Dict]:
        """Calculate Double Exponential Moving Average

        DEMA = 2 * EMA(close, period) - EMA(EMA(close, period), period)
        Reduces lag compared to regular EMA.
        """
        ema1 = df['close'].ewm(span=period, adjust=False).mean()
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        dema = 2 * ema1 - ema2

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'dema': dema.iloc[i] if not pd.isna(dema.iloc[i]) else None
            })
        return result

    def calculate_tema(self, df: pd.DataFrame, period: int = 20) -> List[Dict]:
        """Calculate Triple Exponential Moving Average

        TEMA = 3*EMA - 3*EMA(EMA) + EMA(EMA(EMA))
        Further reduces lag for faster response to price changes.
        """
        ema1 = df['close'].ewm(span=period, adjust=False).mean()
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        ema3 = ema2.ewm(span=period, adjust=False).mean()
        tema = 3 * ema1 - 3 * ema2 + ema3

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'tema': tema.iloc[i] if not pd.isna(tema.iloc[i]) else None
            })
        return result

    def calculate_supertrend(self, df: pd.DataFrame, period: int = 10, multiplier: int = 3) -> List[Dict]:
        """Calculate Supertrend Indicator

        Supertrend is a trend-following indicator based on ATR.
        """
        atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=period).average_true_range()

        hl2 = (df['high'] + df['low']) / 2
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)

        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)

        for i in range(period, len(df)):
            if i == period:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                if df['close'].iloc[i] > supertrend.iloc[i-1]:
                    supertrend.iloc[i] = max(lower_band.iloc[i], supertrend.iloc[i-1]) if direction.iloc[i-1] == 1 else lower_band.iloc[i]
                    direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = min(upper_band.iloc[i], supertrend.iloc[i-1]) if direction.iloc[i-1] == -1 else upper_band.iloc[i]
                    direction.iloc[i] = -1

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'supertrend': supertrend.iloc[i] if not pd.isna(supertrend.iloc[i]) else None,
                'direction': int(direction.iloc[i]) if not pd.isna(direction.iloc[i]) else None
            })
        return result

    def calculate_ichimoku(self, df: pd.DataFrame, tenkan_period: int = 9, kijun_period: int = 26, senkou_b_period: int = 52) -> List[Dict]:
        """Calculate Ichimoku Cloud

        Returns Tenkan-sen, Kijun-sen, Senkou Span A, Senkou Span B, and Chikou Span.
        """
        ichimoku = ta.trend.IchimokuIndicator(
            df['high'], df['low'],
            window1=tenkan_period, window2=kijun_period, window3=senkou_b_period
        )

        tenkan = ichimoku.ichimoku_conversion_line()
        kijun = ichimoku.ichimoku_base_line()
        senkou_a = ichimoku.ichimoku_a()
        senkou_b = ichimoku.ichimoku_b()
        chikou = df['close'].shift(-kijun_period)

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'tenkan': tenkan.iloc[i] if not pd.isna(tenkan.iloc[i]) else None,
                'kijun': kijun.iloc[i] if not pd.isna(kijun.iloc[i]) else None,
                'senkou_a': senkou_a.iloc[i] if not pd.isna(senkou_a.iloc[i]) else None,
                'senkou_b': senkou_b.iloc[i] if not pd.isna(senkou_b.iloc[i]) else None,
                'chikou': chikou.iloc[i] if i < len(chikou) and not pd.isna(chikou.iloc[i]) else None
            })
        return result

    def calculate_aroon(self, df: pd.DataFrame, period: int = 25) -> List[Dict]:
        """Calculate Aroon Indicator

        Aroon Up and Aroon Down identify trend changes and strength.
        """
        aroon = ta.trend.AroonIndicator(df['high'], df['low'], window=period)
        aroon_up = aroon.aroon_up()
        aroon_down = aroon.aroon_down()
        aroon_indicator = aroon.aroon_indicator()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'aroon_up': aroon_up.iloc[i] if not pd.isna(aroon_up.iloc[i]) else None,
                'aroon_down': aroon_down.iloc[i] if not pd.isna(aroon_down.iloc[i]) else None,
                'aroon_indicator': aroon_indicator.iloc[i] if not pd.isna(aroon_indicator.iloc[i]) else None
            })
        return result

    def calculate_vortex(self, df: pd.DataFrame, period: int = 14) -> List[Dict]:
        """Calculate Vortex Indicator

        VI+ and VI- identify trend direction and reversals.
        """
        vortex = ta.trend.VortexIndicator(df['high'], df['low'], df['close'], window=period)
        vi_pos = vortex.vortex_indicator_pos()
        vi_neg = vortex.vortex_indicator_neg()
        vi_diff = vortex.vortex_indicator_diff()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'vi_pos': vi_pos.iloc[i] if not pd.isna(vi_pos.iloc[i]) else None,
                'vi_neg': vi_neg.iloc[i] if not pd.isna(vi_neg.iloc[i]) else None,
                'vi_diff': vi_diff.iloc[i] if not pd.isna(vi_diff.iloc[i]) else None
            })
        return result

    # ================================================================
    # NEW MOMENTUM INDICATORS
    # ================================================================

    def calculate_stochastic_rsi(self, df: pd.DataFrame, period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> List[Dict]:
        """Calculate Stochastic RSI

        Applies Stochastic formula to RSI values for more sensitive signals.
        """
        stoch_rsi = ta.momentum.StochRSIIndicator(df['close'], window=period, smooth1=smooth_k, smooth2=smooth_d)
        stoch_rsi_k = stoch_rsi.stochrsi_k()
        stoch_rsi_d = stoch_rsi.stochrsi_d()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'stoch_rsi_k': stoch_rsi_k.iloc[i] * 100 if not pd.isna(stoch_rsi_k.iloc[i]) else None,
                'stoch_rsi_d': stoch_rsi_d.iloc[i] * 100 if not pd.isna(stoch_rsi_d.iloc[i]) else None
            })
        return result

    def calculate_momentum(self, df: pd.DataFrame, period: int = 10) -> List[Dict]:
        """Calculate Momentum Indicator

        Measures the rate of change in price over a period.
        MOM = Close - Close(n periods ago)
        """
        momentum = df['close'] - df['close'].shift(period)

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'momentum': momentum.iloc[i] if not pd.isna(momentum.iloc[i]) else None
            })
        return result

    def calculate_tsi(self, df: pd.DataFrame, long_period: int = 25, short_period: int = 13, signal_period: int = 13) -> List[Dict]:
        """Calculate True Strength Index

        Double-smoothed momentum indicator showing trend direction and overbought/oversold conditions.
        """
        tsi = ta.momentum.TSIIndicator(df['close'], window_slow=long_period, window_fast=short_period)
        tsi_value = tsi.tsi()

        # Calculate signal line
        tsi_signal = tsi_value.ewm(span=signal_period, adjust=False).mean()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'tsi': tsi_value.iloc[i] if not pd.isna(tsi_value.iloc[i]) else None,
                'tsi_signal': tsi_signal.iloc[i] if not pd.isna(tsi_signal.iloc[i]) else None
            })
        return result

    def calculate_ultimate_oscillator(self, df: pd.DataFrame, short_period: int = 7, medium_period: int = 14, long_period: int = 28) -> List[Dict]:
        """Calculate Ultimate Oscillator

        Combines short, medium, and long-term momentum.
        """
        uo = ta.momentum.UltimateOscillator(
            df['high'], df['low'], df['close'],
            window1=short_period, window2=medium_period, window3=long_period
        ).ultimate_oscillator()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'uo': uo.iloc[i] if not pd.isna(uo.iloc[i]) else None
            })
        return result

    def calculate_awesome_oscillator(self, df: pd.DataFrame, fast_period: int = 5, slow_period: int = 34) -> List[Dict]:
        """Calculate Awesome Oscillator

        Measures market momentum using SMA of median prices.
        AO = SMA(median, 5) - SMA(median, 34)
        """
        ao = ta.momentum.AwesomeOscillatorIndicator(
            df['high'], df['low'],
            window1=fast_period, window2=slow_period
        ).awesome_oscillator()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'ao': ao.iloc[i] if not pd.isna(ao.iloc[i]) else None
            })
        return result

    # ================================================================
    # NEW VOLATILITY INDICATORS
    # ================================================================

    def calculate_std_dev(self, df: pd.DataFrame, period: int = 20) -> List[Dict]:
        """Calculate Standard Deviation

        Statistical measure of price dispersion and volatility.
        """
        std_dev = df['close'].rolling(window=period).std()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'std_dev': std_dev.iloc[i] if not pd.isna(std_dev.iloc[i]) else None
            })
        return result

    def calculate_historical_volatility(self, df: pd.DataFrame, period: int = 20) -> List[Dict]:
        """Calculate Historical Volatility

        Annualized standard deviation of log returns.
        """
        log_returns = np.log(df['close'] / df['close'].shift(1))
        hv = log_returns.rolling(window=period).std() * np.sqrt(252) * 100  # Annualized

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'hv': hv.iloc[i] if not pd.isna(hv.iloc[i]) else None
            })
        return result

    # ================================================================
    # NEW VOLUME INDICATORS
    # ================================================================

    def calculate_volume(self, df: pd.DataFrame) -> List[Dict]:
        """Return raw trading volume"""
        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'volume': df['volume'].iloc[i] if not pd.isna(df['volume'].iloc[i]) else None
            })
        return result

    def calculate_chaikin_oscillator(self, df: pd.DataFrame, fast_period: int = 3, slow_period: int = 10) -> List[Dict]:
        """Calculate Chaikin Oscillator

        MACD applied to A/D Line. Measures momentum of accumulation/distribution.
        """
        ad = ta.volume.AccDistIndexIndicator(df['high'], df['low'], df['close'], df['volume']).acc_dist_index()
        ema_fast = ad.ewm(span=fast_period, adjust=False).mean()
        ema_slow = ad.ewm(span=slow_period, adjust=False).mean()
        cho = ema_fast - ema_slow

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'cho': cho.iloc[i] if not pd.isna(cho.iloc[i]) else None
            })
        return result

    def calculate_volume_oscillator(self, df: pd.DataFrame, fast_period: int = 5, slow_period: int = 10) -> List[Dict]:
        """Calculate Volume Oscillator

        Percentage difference between two volume moving averages.
        """
        vol_fast = df['volume'].rolling(window=fast_period).mean()
        vol_slow = df['volume'].rolling(window=slow_period).mean()
        vosc = ((vol_fast - vol_slow) / vol_slow) * 100

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'vosc': vosc.iloc[i] if not pd.isna(vosc.iloc[i]) else None
            })
        return result

    def calculate_eom(self, df: pd.DataFrame, period: int = 14) -> List[Dict]:
        """Calculate Ease of Movement

        Relates price change to volume, showing how easily price moves.
        """
        eom = ta.volume.EaseOfMovementIndicator(
            df['high'], df['low'], df['volume'], window=period
        ).ease_of_movement()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'eom': eom.iloc[i] if not pd.isna(eom.iloc[i]) else None
            })
        return result

    def calculate_force_index(self, df: pd.DataFrame, period: int = 13) -> List[Dict]:
        """Calculate Force Index

        Combines price movement and volume to measure buying/selling pressure.
        """
        fi = ta.volume.ForceIndexIndicator(df['close'], df['volume'], window=period).force_index()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'fi': fi.iloc[i] if not pd.isna(fi.iloc[i]) else None
            })
        return result

    def calculate_nvi(self, df: pd.DataFrame) -> List[Dict]:
        """Calculate Negative Volume Index

        Cumulative indicator that changes only on down-volume days.
        Tracks 'smart money' activity.
        """
        nvi = ta.volume.NegativeVolumeIndexIndicator(df['close'], df['volume']).negative_volume_index()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'nvi': nvi.iloc[i] if not pd.isna(nvi.iloc[i]) else None
            })
        return result

    def calculate_pvi(self, df: pd.DataFrame) -> List[Dict]:
        """Calculate Positive Volume Index

        Cumulative indicator that changes only on up-volume days.
        Tracks 'crowd' behavior.
        """
        # PVI calculation - changes when volume increases
        pvi = pd.Series(index=df.index, dtype=float)
        pvi.iloc[0] = 1000  # Starting value

        for i in range(1, len(df)):
            if df['volume'].iloc[i] > df['volume'].iloc[i-1]:
                pvi.iloc[i] = pvi.iloc[i-1] * (1 + (df['close'].iloc[i] - df['close'].iloc[i-1]) / df['close'].iloc[i-1])
            else:
                pvi.iloc[i] = pvi.iloc[i-1]

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'pvi': pvi.iloc[i] if not pd.isna(pvi.iloc[i]) else None
            })
        return result

    # ================================================================
    # SUPPORT & RESISTANCE INDICATORS
    # ================================================================

    def calculate_pivot_points(self, df: pd.DataFrame, type: str = 'standard') -> List[Dict]:
        """Calculate Pivot Points

        Calculates support/resistance levels based on previous period's high, low, close.
        """
        result = []
        for i, date in enumerate(df.index):
            if i == 0:
                result.append({
                    'date': date.isoformat(),
                    'pivot': None, 'r1': None, 'r2': None, 'r3': None,
                    's1': None, 's2': None, 's3': None
                })
                continue

            high = df['high'].iloc[i-1]
            low = df['low'].iloc[i-1]
            close = df['close'].iloc[i-1]

            pivot = (high + low + close) / 3
            r1 = 2 * pivot - low
            s1 = 2 * pivot - high
            r2 = pivot + (high - low)
            s2 = pivot - (high - low)
            r3 = high + 2 * (pivot - low)
            s3 = low - 2 * (high - pivot)

            result.append({
                'date': date.isoformat(),
                'pivot': pivot,
                'r1': r1, 'r2': r2, 'r3': r3,
                's1': s1, 's2': s2, 's3': s3
            })
        return result

    def calculate_fibonacci_retracement(self, df: pd.DataFrame) -> List[Dict]:
        """Calculate Fibonacci Retracement Levels

        Key retracement levels for potential support/resistance.
        """
        # Find swing high and swing low over the entire period
        swing_high = df['high'].max()
        swing_low = df['low'].min()
        diff = swing_high - swing_low

        fib_levels = {
            'level_0': swing_high,
            'level_236': swing_high - diff * 0.236,
            'level_382': swing_high - diff * 0.382,
            'level_500': swing_high - diff * 0.5,
            'level_618': swing_high - diff * 0.618,
            'level_786': swing_high - diff * 0.786,
            'level_100': swing_low
        }

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                **fib_levels
            })
        return result

    def calculate_fibonacci_extension(self, df: pd.DataFrame) -> List[Dict]:
        """Calculate Fibonacci Extension Levels

        Projects price targets beyond the current move.
        """
        swing_high = df['high'].max()
        swing_low = df['low'].min()
        diff = swing_high - swing_low

        ext_levels = {
            'ext_0': swing_low,
            'ext_618': swing_low + diff * 0.618,
            'ext_100': swing_high,
            'ext_1618': swing_low + diff * 1.618,
            'ext_2618': swing_low + diff * 2.618,
            'ext_4236': swing_low + diff * 4.236
        }

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                **ext_levels
            })
        return result

    # ================================================================
    # PRICE TRANSFORM INDICATORS
    # ================================================================

    def calculate_heikin_ashi(self, df: pd.DataFrame) -> List[Dict]:
        """Calculate Heikin Ashi Candles

        Modified candlesticks that filter noise and show clearer trends.
        """
        ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        ha_open = pd.Series(index=df.index, dtype=float)
        ha_open.iloc[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2

        for i in range(1, len(df)):
            ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2

        ha_high = pd.concat([df['high'], ha_open, ha_close], axis=1).max(axis=1)
        ha_low = pd.concat([df['low'], ha_open, ha_close], axis=1).min(axis=1)

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'ha_open': ha_open.iloc[i] if not pd.isna(ha_open.iloc[i]) else None,
                'ha_high': ha_high.iloc[i] if not pd.isna(ha_high.iloc[i]) else None,
                'ha_low': ha_low.iloc[i] if not pd.isna(ha_low.iloc[i]) else None,
                'ha_close': ha_close.iloc[i] if not pd.isna(ha_close.iloc[i]) else None
            })
        return result

    def calculate_renko(self, df: pd.DataFrame, box_size: float = 1) -> List[Dict]:
        """Calculate Renko Chart Data

        Time-independent chart showing price movements of a specified size.
        Note: This returns traditional OHLC data with Renko-style signals.
        """
        # Calculate ATR-based box size if box_size is not specified meaningfully
        if box_size <= 0:
            atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
            box_size = atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else df['close'].iloc[-1] * 0.01

        renko_direction = pd.Series(index=df.index, dtype=int)
        renko_direction.iloc[0] = 0

        for i in range(1, len(df)):
            price_change = df['close'].iloc[i] - df['close'].iloc[i-1]
            if price_change >= box_size:
                renko_direction.iloc[i] = 1  # Up brick
            elif price_change <= -box_size:
                renko_direction.iloc[i] = -1  # Down brick
            else:
                renko_direction.iloc[i] = renko_direction.iloc[i-1]

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'close': df['close'].iloc[i],
                'renko_direction': int(renko_direction.iloc[i]) if not pd.isna(renko_direction.iloc[i]) else None,
                'box_size': box_size
            })
        return result

    def calculate_typical_price(self, df: pd.DataFrame) -> List[Dict]:
        """Calculate Typical Price

        Average of high, low, and close: (H+L+C)/3
        """
        tp = (df['high'] + df['low'] + df['close']) / 3

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'typical_price': tp.iloc[i] if not pd.isna(tp.iloc[i]) else None
            })
        return result

    def calculate_median_price(self, df: pd.DataFrame) -> List[Dict]:
        """Calculate Median Price

        Midpoint of high and low: (H+L)/2
        """
        mp = (df['high'] + df['low']) / 2

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'median_price': mp.iloc[i] if not pd.isna(mp.iloc[i]) else None
            })
        return result

    def calculate_weighted_close(self, df: pd.DataFrame) -> List[Dict]:
        """Calculate Weighted Close

        Gives double weight to closing price: (H+L+2*C)/4
        """
        wc = (df['high'] + df['low'] + 2 * df['close']) / 4

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'weighted_close': wc.iloc[i] if not pd.isna(wc.iloc[i]) else None
            })
        return result

    # ================================================================
    # BILL WILLIAMS INDICATORS
    # ================================================================

    def calculate_alligator(self, df: pd.DataFrame, jaw_period: int = 13, teeth_period: int = 8, lips_period: int = 5) -> List[Dict]:
        """Calculate Williams Alligator

        Three smoothed moving averages (Jaw, Teeth, Lips) that identify trends.
        """
        median_price = (df['high'] + df['low']) / 2

        # Smoothed moving averages with forward shifts
        jaw = median_price.rolling(window=jaw_period).mean().shift(8)  # Blue, shifted 8 bars
        teeth = median_price.rolling(window=teeth_period).mean().shift(5)  # Red, shifted 5 bars
        lips = median_price.rolling(window=lips_period).mean().shift(3)  # Green, shifted 3 bars

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'jaw': jaw.iloc[i] if not pd.isna(jaw.iloc[i]) else None,
                'teeth': teeth.iloc[i] if not pd.isna(teeth.iloc[i]) else None,
                'lips': lips.iloc[i] if not pd.isna(lips.iloc[i]) else None
            })
        return result

    def calculate_fractals(self, df: pd.DataFrame) -> List[Dict]:
        """Calculate Williams Fractals

        Identifies potential reversal points using 5-bar pattern recognition.
        """
        fractal_up = pd.Series(index=df.index, dtype=float)
        fractal_down = pd.Series(index=df.index, dtype=float)

        for i in range(2, len(df) - 2):
            # Bullish fractal (arrow down) - highest high in 5 bars
            if (df['high'].iloc[i] > df['high'].iloc[i-1] and
                df['high'].iloc[i] > df['high'].iloc[i-2] and
                df['high'].iloc[i] > df['high'].iloc[i+1] and
                df['high'].iloc[i] > df['high'].iloc[i+2]):
                fractal_up.iloc[i] = df['high'].iloc[i]

            # Bearish fractal (arrow up) - lowest low in 5 bars
            if (df['low'].iloc[i] < df['low'].iloc[i-1] and
                df['low'].iloc[i] < df['low'].iloc[i-2] and
                df['low'].iloc[i] < df['low'].iloc[i+1] and
                df['low'].iloc[i] < df['low'].iloc[i+2]):
                fractal_down.iloc[i] = df['low'].iloc[i]

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'fractal_up': fractal_up.iloc[i] if not pd.isna(fractal_up.iloc[i]) else None,
                'fractal_down': fractal_down.iloc[i] if not pd.isna(fractal_down.iloc[i]) else None
            })
        return result

    def calculate_gator_oscillator(self, df: pd.DataFrame, jaw_period: int = 13, teeth_period: int = 8, lips_period: int = 5) -> List[Dict]:
        """Calculate Gator Oscillator

        Shows the degree of convergence/divergence of Alligator lines.
        """
        median_price = (df['high'] + df['low']) / 2

        jaw = median_price.rolling(window=jaw_period).mean().shift(8)
        teeth = median_price.rolling(window=teeth_period).mean().shift(5)
        lips = median_price.rolling(window=lips_period).mean().shift(3)

        # Upper histogram: |Jaw - Teeth|
        gator_upper = (jaw - teeth).abs()
        # Lower histogram: -|Teeth - Lips|
        gator_lower = -(teeth - lips).abs()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'gator_upper': gator_upper.iloc[i] if not pd.isna(gator_upper.iloc[i]) else None,
                'gator_lower': gator_lower.iloc[i] if not pd.isna(gator_lower.iloc[i]) else None
            })
        return result

    def calculate_mfi_bw(self, df: pd.DataFrame) -> List[Dict]:
        """Calculate Market Facilitation Index (Bill Williams)

        Measures price movement efficiency relative to volume.
        MFI = (High - Low) / Volume
        """
        mfi_bw = (df['high'] - df['low']) / df['volume']

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'mfi_bw': mfi_bw.iloc[i] if not pd.isna(mfi_bw.iloc[i]) else None
            })
        return result

    def calculate_accelerator_oscillator(self, df: pd.DataFrame, fast_period: int = 5, slow_period: int = 34) -> List[Dict]:
        """Calculate Accelerator Oscillator

        Measures acceleration/deceleration of market momentum.
        AC = AO - SMA(AO, 5)
        """
        # First calculate Awesome Oscillator
        median_price = (df['high'] + df['low']) / 2
        ao = median_price.rolling(window=fast_period).mean() - median_price.rolling(window=slow_period).mean()

        # Then calculate Accelerator Oscillator
        ac = ao - ao.rolling(window=5).mean()

        result = []
        for i, date in enumerate(df.index):
            result.append({
                'date': date.isoformat(),
                'ac': ac.iloc[i] if not pd.isna(ac.iloc[i]) else None
            })
        return result

    def get_available_indicators(self) -> Dict[str, List[str]]:
        """Get all available indicators grouped by category"""
        indicators_by_category = {}

        for indicator_name, config in self.indicators_config.items():
            category = config.category.value
            if category not in indicators_by_category:
                indicators_by_category[category] = []
            indicators_by_category[category].append({
                'name': indicator_name,
                'description': config.description,
                'parameters': config.parameters
            })

        return indicators_by_category

    def get_indicator_categories(self) -> List[str]:
        """Get list of indicator categories"""
        return [category.value for category in IndicatorCategory]