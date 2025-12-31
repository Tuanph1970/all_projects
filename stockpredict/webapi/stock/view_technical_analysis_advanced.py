"""
Advanced Technical Analysis API Views
Provides comprehensive technical analysis data for stocks including
indicators, patterns, signals, and trading recommendations.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from services.stock_entities import StockService, DataSource, Interval

logger = logging.getLogger(__name__)

def calculate_sma(prices, period):
    """Calculate Simple Moving Average"""
    return prices.rolling(window=period).mean()

def calculate_ema(prices, period):
    """Calculate Exponential Moving Average"""
    return prices.ewm(span=period, adjust=False).mean()

def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD (Moving Average Convergence Divergence)"""
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return upper_band, sma, lower_band

def calculate_stochastic(high, low, close, period=14):
    """Calculate Stochastic Oscillator"""
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=3).mean()
    return k_percent, d_percent

def calculate_atr(high, low, close, period=14):
    """Calculate Average True Range (ATR)"""
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = pd.Series(true_range).rolling(window=period).mean()
    return atr

def calculate_obv(prices, volumes):
    """Calculate On-Balance Volume (OBV)"""
    obv_series = (np.sign(prices.diff()) * volumes)
    obv = obv_series.infer_objects(copy=False).fillna(0).cumsum()
    return obv

def calculate_fibonacci_retracements(high, low):
    """Calculate Fibonacci Retracement Levels"""
    diff = high - low
    levels = {
        '0.0%': high,
        '23.6%': high - (diff * 0.236),
        '38.2%': high - (diff * 0.382),
        '50.0%': high - (diff * 0.5),
        '61.8%': high - (diff * 0.618),
        '78.6%': high - (diff * 0.786),
        '100.0%': low
    }
    return levels

def identify_support_resistance(prices, window=20):
    """Identify support and resistance levels"""
    # Find local maxima and minima
    rolling_max = prices.rolling(window=window, center=True).max()
    rolling_min = prices.rolling(window=window, center=True).min()
    
    resistance_levels = prices[prices == rolling_max].unique()
    support_levels = prices[prices == rolling_min].unique()
    
    # Take top 3 most significant levels
    resistance_levels = sorted(resistance_levels, reverse=True)[:3]
    support_levels = sorted(support_levels)[:3]
    
    return support_levels, resistance_levels

def generate_trading_signals(df):
    """Generate trading signals based on technical indicators"""
    signals = []
    score = 0
    
    # Get latest values
    latest = df.iloc[-1] if len(df) > 0 else None
    
    if latest is not None:
        # RSI Signal
        if 'RSI' in df.columns:
            if latest['RSI'] < 30:
                signals.append({'indicator': 'RSI', 'signal': 'BUY', 'value': latest['RSI'], 'reason': 'Oversold condition'})
                score += 20
            elif latest['RSI'] > 70:
                signals.append({'indicator': 'RSI', 'signal': 'SELL', 'value': latest['RSI'], 'reason': 'Overbought condition'})
                score -= 20
            else:
                signals.append({'indicator': 'RSI', 'signal': 'NEUTRAL', 'value': latest['RSI'], 'reason': 'Normal range'})
        
        # MACD Signal
        if 'MACD' in df.columns and 'MACD_Signal' in df.columns:
            if latest['MACD'] > latest['MACD_Signal'] and df['MACD'].iloc[-2] <= df['MACD_Signal'].iloc[-2]:
                signals.append({'indicator': 'MACD', 'signal': 'BUY', 'value': latest['MACD'], 'reason': 'Bullish crossover'})
                score += 15
            elif latest['MACD'] < latest['MACD_Signal'] and df['MACD'].iloc[-2] >= df['MACD_Signal'].iloc[-2]:
                signals.append({'indicator': 'MACD', 'signal': 'SELL', 'value': latest['MACD'], 'reason': 'Bearish crossover'})
                score -= 15
            else:
                signals.append({'indicator': 'MACD', 'signal': 'NEUTRAL', 'value': latest['MACD'], 'reason': 'No crossover'})
        
        # Moving Average Signal
        if 'SMA_50' in df.columns and 'SMA_200' in df.columns:
            if latest['close'] > latest['SMA_50'] > latest['SMA_200']:
                signals.append({'indicator': 'Moving Averages', 'signal': 'BUY', 'value': latest['close'], 'reason': 'Golden cross pattern'})
                score += 25
            elif latest['close'] < latest['SMA_50'] < latest['SMA_200']:
                signals.append({'indicator': 'Moving Averages', 'signal': 'SELL', 'value': latest['close'], 'reason': 'Death cross pattern'})
                score -= 25
            else:
                signals.append({'indicator': 'Moving Averages', 'signal': 'NEUTRAL', 'value': latest['close'], 'reason': 'Mixed signals'})
        
        # Bollinger Bands Signal
        if 'BB_Upper' in df.columns and 'BB_Lower' in df.columns:
            if latest['close'] < latest['BB_Lower']:
                signals.append({'indicator': 'Bollinger Bands', 'signal': 'BUY', 'value': latest['close'], 'reason': 'Price below lower band'})
                score += 10
            elif latest['close'] > latest['BB_Upper']:
                signals.append({'indicator': 'Bollinger Bands', 'signal': 'SELL', 'value': latest['close'], 'reason': 'Price above upper band'})
                score -= 10
            else:
                signals.append({'indicator': 'Bollinger Bands', 'signal': 'NEUTRAL', 'value': latest['close'], 'reason': 'Price within bands'})
        
        # Volume Signal
        if 'volume' in df.columns:
            avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
            if latest['volume'] > avg_volume * 1.5:
                if latest['close'] > df['close'].iloc[-2]:
                    signals.append({'indicator': 'Volume', 'signal': 'BUY', 'value': latest['volume'], 'reason': 'High volume on price increase'})
                    score += 10
                else:
                    signals.append({'indicator': 'Volume', 'signal': 'SELL', 'value': latest['volume'], 'reason': 'High volume on price decrease'})
                    score -= 10
            else:
                signals.append({'indicator': 'Volume', 'signal': 'NEUTRAL', 'value': latest['volume'], 'reason': 'Normal volume'})
    
    # Determine overall recommendation
    if score >= 30:
        recommendation = 'STRONG BUY'
    elif score >= 15:
        recommendation = 'BUY'
    elif score <= -30:
        recommendation = 'STRONG SELL'
    elif score <= -15:
        recommendation = 'SELL'
    else:
        recommendation = 'HOLD'
    
    return {
        'signals': signals,
        'score': score,
        'recommendation': recommendation
    }

@csrf_exempt
@api_view(['GET'])
def get_technical_analysis(request, symbol):
    """
    Get comprehensive technical analysis data for a stock symbol
    
    Args:
        symbol: Stock ticker symbol (e.g., 'VIC', 'VNM')
        period: Number of days to analyze (default: 100)
        
    Returns:
        JSON response with technical analysis data
    """
    try:
        period_days = int(request.GET.get('period', 100))
        
        # Initialize stock service
        service = StockService(symbol=symbol, source=DataSource.VCI.value)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Get historical price data
        price_data = service.get_price_history(
            symbol=symbol,
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval=Interval.ONE_DAY.value
        )
        
        if price_data.empty:
            return Response(
                {'error': f'No price data available for {symbol}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ensure we have required columns
        if 'close' not in price_data.columns:
            return Response(
                {'error': 'Price data missing required columns'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate Moving Averages
        price_data['SMA_20'] = calculate_sma(price_data['close'], 20)
        price_data['SMA_50'] = calculate_sma(price_data['close'], 50)
        price_data['SMA_200'] = calculate_sma(price_data['close'], 200)
        price_data['EMA_12'] = calculate_ema(price_data['close'], 12)
        price_data['EMA_26'] = calculate_ema(price_data['close'], 26)
        
        # Calculate RSI
        price_data['RSI'] = calculate_rsi(price_data['close'])
        
        # Calculate MACD
        macd, signal, histogram = calculate_macd(price_data['close'])
        price_data['MACD'] = macd
        price_data['MACD_Signal'] = signal
        price_data['MACD_Histogram'] = histogram
        
        # Calculate Bollinger Bands
        upper, middle, lower = calculate_bollinger_bands(price_data['close'])
        price_data['BB_Upper'] = upper
        price_data['BB_Middle'] = middle
        price_data['BB_Lower'] = lower
        
        # Calculate Stochastic Oscillator
        if 'high' in price_data.columns and 'low' in price_data.columns:
            k_percent, d_percent = calculate_stochastic(
                price_data['high'], 
                price_data['low'], 
                price_data['close']
            )
            price_data['Stoch_K'] = k_percent
            price_data['Stoch_D'] = d_percent
            
            # Calculate ATR
            price_data['ATR'] = calculate_atr(
                price_data['high'],
                price_data['low'],
                price_data['close']
            )
        
        # Calculate OBV
        if 'volume' in price_data.columns:
            price_data['OBV'] = calculate_obv(price_data['close'], price_data['volume'])
        
        # Identify Support and Resistance levels
        support_levels, resistance_levels = identify_support_resistance(price_data['close'])
        
        # Calculate Fibonacci levels
        period_high = price_data['high'].max() if 'high' in price_data.columns else price_data['close'].max()
        period_low = price_data['low'].min() if 'low' in price_data.columns else price_data['close'].min()
        fibonacci_levels = calculate_fibonacci_retracements(period_high, period_low)
        
        # Generate trading signals
        trading_analysis = generate_trading_signals(price_data)
        
        # Get latest values for current indicators
        latest_data = price_data.iloc[-1] if len(price_data) > 0 else {}
        
        # Prepare response data
        analysis_data = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'period': f'{period_days} days',
            
            # Current Price Information
            'current_price': {
                'price': float(latest_data.get('close', 0)),
                'volume': int(latest_data.get('volume', 0)),
                'high': float(latest_data.get('high', 0)),
                'low': float(latest_data.get('low', 0)),
                'open': float(latest_data.get('open', 0))
            },
            
            # Moving Averages
            'moving_averages': {
                'SMA_20': float(latest_data.get('SMA_20', 0)) if pd.notna(latest_data.get('SMA_20')) else None,
                'SMA_50': float(latest_data.get('SMA_50', 0)) if pd.notna(latest_data.get('SMA_50')) else None,
                'SMA_200': float(latest_data.get('SMA_200', 0)) if pd.notna(latest_data.get('SMA_200')) else None,
                'EMA_12': float(latest_data.get('EMA_12', 0)) if pd.notna(latest_data.get('EMA_12')) else None,
                'EMA_26': float(latest_data.get('EMA_26', 0)) if pd.notna(latest_data.get('EMA_26')) else None
            },
            
            # Momentum Indicators
            'momentum_indicators': {
                'RSI': float(latest_data.get('RSI', 0)) if pd.notna(latest_data.get('RSI')) else None,
                'MACD': float(latest_data.get('MACD', 0)) if pd.notna(latest_data.get('MACD')) else None,
                'MACD_Signal': float(latest_data.get('MACD_Signal', 0)) if pd.notna(latest_data.get('MACD_Signal')) else None,
                'MACD_Histogram': float(latest_data.get('MACD_Histogram', 0)) if pd.notna(latest_data.get('MACD_Histogram')) else None,
                'Stoch_K': float(latest_data.get('Stoch_K', 0)) if pd.notna(latest_data.get('Stoch_K')) else None,
                'Stoch_D': float(latest_data.get('Stoch_D', 0)) if pd.notna(latest_data.get('Stoch_D')) else None
            },
            
            # Volatility Indicators
            'volatility_indicators': {
                'BB_Upper': float(latest_data.get('BB_Upper', 0)) if pd.notna(latest_data.get('BB_Upper')) else None,
                'BB_Middle': float(latest_data.get('BB_Middle', 0)) if pd.notna(latest_data.get('BB_Middle')) else None,
                'BB_Lower': float(latest_data.get('BB_Lower', 0)) if pd.notna(latest_data.get('BB_Lower')) else None,
                'ATR': float(latest_data.get('ATR', 0)) if pd.notna(latest_data.get('ATR')) else None
            },
            
            # Volume Indicators
            'volume_indicators': {
                'OBV': float(latest_data.get('OBV', 0)) if pd.notna(latest_data.get('OBV')) else None,
                'volume_avg_20': float(price_data['volume'].rolling(window=20).mean().iloc[-1]) if 'volume' in price_data.columns else None
            },
            
            # Support and Resistance
            'support_resistance': {
                'support_levels': [float(x) for x in support_levels],
                'resistance_levels': [float(x) for x in resistance_levels]
            },
            
            # Fibonacci Levels
            'fibonacci_levels': {k: float(v) for k, v in fibonacci_levels.items()},
            
            # Trading Signals and Recommendation
            'trading_analysis': trading_analysis,
            
            # Historical data for charts (last 30 data points for efficiency)
            'chart_data': {
                'dates': price_data.index[-30:].strftime('%Y-%m-%d').tolist() if hasattr(price_data.index, 'strftime') else [f"Day {i}" for i in range(len(price_data.index[-30:]))],
                'prices': price_data['close'][-30:].tolist(),
                'volumes': price_data['volume'][-30:].tolist() if 'volume' in price_data.columns else [],
                'sma_20': price_data['SMA_20'][-30:].infer_objects(copy=False).fillna(0).tolist(),
                'sma_50': price_data['SMA_50'][-30:].infer_objects(copy=False).fillna(0).tolist(),
                'bb_upper': price_data['BB_Upper'][-30:].infer_objects(copy=False).fillna(0).tolist(),
                'bb_lower': price_data['BB_Lower'][-30:].infer_objects(copy=False).fillna(0).tolist(),
                'rsi': price_data['RSI'][-30:].infer_objects(copy=False).fillna(0).tolist()
            }
        }
        
        return Response(analysis_data, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response(
            {'error': 'Invalid period parameter', 'details': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error in technical analysis for {symbol}: {e}")
        return Response(
            {'error': f'Failed to get technical analysis for {symbol}', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['GET'])
def get_technical_indicators(request, symbol):
    """
    Get specific technical indicators for a stock
    
    Args:
        symbol: Stock ticker symbol
        indicators: Comma-separated list of indicators (e.g., 'rsi,macd,sma')
        period: Number of days (default: 30)
        
    Returns:
        JSON response with requested indicators
    """
    try:
        indicators = request.GET.get('indicators', 'rsi,macd,sma').split(',')
        period_days = int(request.GET.get('period', 30))
        
        # Initialize stock service
        service = StockService(symbol=symbol, source=DataSource.VCI.value)
        
        # Get technical indicators from service
        technical_data = service.get_technical_indicators(symbol)
        
        response_data = {
            'symbol': symbol,
            'period': f'{period_days} days',
            'indicators': technical_data,
            'timestamp': datetime.now().isoformat()
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting technical indicators for {symbol}: {e}")
        return Response(
            {'error': f'Failed to get technical indicators for {symbol}', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['GET'])
def get_intraday_analysis(request, symbol):
    """
    Get intraday technical analysis for a stock
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        JSON response with intraday analysis
    """
    try:
        # Initialize stock service
        service = StockService(symbol=symbol, source=DataSource.VCI.value)
        
        # Get intraday data
        intraday_data = service.get_intraday_data(symbol, page_size=1000)
        
        if intraday_data.empty:
            return Response(
                {'error': f'No intraday data available for {symbol}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate intraday indicators
        if 'close' in intraday_data.columns:
            # Short-term moving averages for intraday
            intraday_data['SMA_5'] = calculate_sma(intraday_data['close'], 5)
            intraday_data['SMA_10'] = calculate_sma(intraday_data['close'], 10)
            
            # RSI for intraday
            intraday_data['RSI'] = calculate_rsi(intraday_data['close'], period=9)
            
            # VWAP (Volume Weighted Average Price)
            if 'volume' in intraday_data.columns:
                intraday_data['VWAP'] = (
                    (intraday_data['close'] * intraday_data['volume']).cumsum() /
                    intraday_data['volume'].cumsum()
                )
        
        # Get latest values
        latest = intraday_data.iloc[-1] if len(intraday_data) > 0 else {}
        
        response_data = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'current': {
                'price': float(latest.get('close', 0)),
                'volume': int(latest.get('volume', 0)),
                'sma_5': float(latest.get('SMA_5', 0)) if pd.notna(latest.get('SMA_5')) else None,
                'sma_10': float(latest.get('SMA_10', 0)) if pd.notna(latest.get('SMA_10')) else None,
                'rsi': float(latest.get('RSI', 0)) if pd.notna(latest.get('RSI')) else None,
                'vwap': float(latest.get('VWAP', 0)) if pd.notna(latest.get('VWAP')) else None
            },
            'intraday_data': intraday_data.tail(100).to_dict('records')  # Last 100 data points
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting intraday analysis for {symbol}: {e}")
        return Response(
            {'error': f'Failed to get intraday analysis for {symbol}', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )