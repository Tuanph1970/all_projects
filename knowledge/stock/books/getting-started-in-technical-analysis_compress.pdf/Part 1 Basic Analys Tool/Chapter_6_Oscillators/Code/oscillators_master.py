"""
Chapter 6: Oscillators - Master Implementation File
Based on "Getting Started in Technical Analysis" by Jack D. Schwager

This module contains implementations of all oscillator concepts from Chapter 6:
- Momentum
- Rate of Change (ROC)
- Moving Average Oscillator
- Price Oscillator
- MACD
- RSI (Relative Strength Index)
- Stochastics (%K and %D)
- Overbought/Oversold detection
- Divergence detection
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# Synthetic price data generator (mimics 3Com-like behavior referenced in Ch.6)
# -----------------------------------------------------------------------------
def generate_synthetic_prices(n_days=200, seed=42, start_price=50.0):
    """Generate a realistic synthetic price series with trends and reversals."""
    np.random.seed(seed)
    prices = [start_price]
    # Phase 1: downtrend (~50 days)
    for _ in range(50):
        prices.append(prices[-1] * (1 + np.random.normal(-0.005, 0.02)))
    # Phase 2: trading range (~40 days)
    for _ in range(40):
        prices.append(prices[-1] * (1 + np.random.normal(0.0, 0.015)))
    # Phase 3: strong uptrend (~70 days)
    for _ in range(70):
        prices.append(prices[-1] * (1 + np.random.normal(0.008, 0.02)))
    # Phase 4: correction (~40 days)
    for _ in range(n_days - 160):
        prices.append(prices[-1] * (1 + np.random.normal(-0.002, 0.018)))
    dates = pd.date_range(end=datetime.today(), periods=len(prices))
    return pd.DataFrame({'date': dates, 'close': prices}).set_index('date')


# -----------------------------------------------------------------------------
# 1. MOMENTUM
# Formula: Momentum(n) = Close[today] - Close[n days ago]
# -----------------------------------------------------------------------------
def momentum(close, n=10):
    """N-day momentum = today's close - close N days ago."""
    return close - close.shift(n)


# -----------------------------------------------------------------------------
# 2. RATE OF CHANGE (ROC)
# Formula: ROC(n) = Close[today] / Close[n days ago] (or expressed as a ratio/%)
# -----------------------------------------------------------------------------
def rate_of_change(close, n=10):
    """N-day ROC = today's close / close N days ago (expressed as ratio)."""
    return close / close.shift(n)


def rate_of_change_pct(close, n=10):
    """N-day ROC expressed as percentage change."""
    return ((close - close.shift(n)) / close.shift(n)) * 100


# -----------------------------------------------------------------------------
# 3. MOVING AVERAGE OSCILLATOR
# Formula: Price - MA(n)
# -----------------------------------------------------------------------------
def ma_oscillator(close, n=20):
    """Moving Average Oscillator = price - n-day moving average."""
    return close - close.rolling(window=n).mean()


# -----------------------------------------------------------------------------
# 4. PRICE OSCILLATOR
# Formula: MA(short) - MA(long)
# -----------------------------------------------------------------------------
def price_oscillator(close, short=10, long=20):
    """Price Oscillator = short MA - long MA."""
    return close.rolling(window=short).mean() - close.rolling(window=long).mean()


# -----------------------------------------------------------------------------
# 5. MACD (Moving Average Convergence Divergence)
# MACD line   = EMA(12) - EMA(26)
# Signal line = EMA(9) of MACD line
# Histogram   = MACD - Signal
# -----------------------------------------------------------------------------
def macd(close, fast=12, slow=26, signal=9):
    """Compute MACD line, signal line, and histogram."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# -----------------------------------------------------------------------------
# 6. RSI (Relative Strength Index) - Welles Wilder Jr., 1978
# RS  = avg up close / avg down close (over n days)
# RSI = 100 - 100/(1 + RS)
# -----------------------------------------------------------------------------
def rsi(close, n=14):
    """Relative Strength Index using Wilder's smoothing."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    # Wilder's smoothing (equivalent to EMA with alpha = 1/n)
    avg_gain = gain.ewm(alpha=1/n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/n, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# -----------------------------------------------------------------------------
# 7. STOCHASTICS (%K and %D)
# %K = ((Close - Low(n)) / (High(n) - Low(n))) * 100
# %D = 3-period MA of %K  (slow %D is a further-smoothed version)
# -----------------------------------------------------------------------------
def stochastic(high, low, close, n=14, d_period=3):
    """Compute fast %K and %D for stochastic oscillator."""
    lowest_low = low.rolling(window=n).min()
    highest_high = high.rolling(window=n).max()
    k = ((close - lowest_low) / (highest_high - lowest_low)) * 100
    d = k.rolling(window=d_period).mean()
    return k, d


def slow_stochastic(high, low, close, n=14, smooth_k=3, d_period=3):
    """Slow stochastic: smooth %K with MA, then take MA of that for %D."""
    fast_k, _ = stochastic(high, low, close, n=n, d_period=1)
    slow_k = fast_k.rolling(window=smooth_k).mean()
    slow_d = slow_k.rolling(window=d_period).mean()
    return slow_k, slow_d


# -----------------------------------------------------------------------------
# 8. OVERBOUGHT / OVERSOLD DETECTION
# -----------------------------------------------------------------------------
def overbought_oversold_signals(indicator, ob_level, os_level):
    """Return boolean Series for overbought and oversold conditions."""
    return indicator > ob_level, indicator < os_level


# -----------------------------------------------------------------------------
# 9. DIVERGENCE DETECTION (simplified pivot-based method)
# Bearish: higher price high, lower oscillator high
# Bullish: lower price low, higher oscillator low
# -----------------------------------------------------------------------------
def find_pivots(series, window=5):
    """Find pivot highs and lows in a series."""
    highs, lows = [], []
    for i in range(window, len(series) - window):
        win = series.iloc[i - window:i + window + 1]
        if series.iloc[i] == win.max():
            highs.append(i)
        if series.iloc[i] == win.min():
            lows.append(i)
    return highs, lows


def detect_divergence(price, oscillator, window=5):
    """Detect bullish/bearish divergences between price and an oscillator."""
    p_highs, p_lows = find_pivots(price, window)
    o_highs, o_lows = find_pivots(oscillator, window)

    bearish, bullish = [], []
    for i in range(1, len(p_highs)):
        prev_p, curr_p = p_highs[i - 1], p_highs[i]
        # find corresponding oscillator pivots near these dates
        prev_o = min(o_highs, key=lambda x: abs(x - prev_p)) if o_highs else None
        curr_o = min(o_highs, key=lambda x: abs(x - curr_p)) if o_highs else None
        if prev_o is None or curr_o is None:
            continue
        if (price.iloc[curr_p] > price.iloc[prev_p] and
                oscillator.iloc[curr_o] < oscillator.iloc[prev_o]):
            bearish.append((curr_p, curr_o))

    for i in range(1, len(p_lows)):
        prev_p, curr_p = p_lows[i - 1], p_lows[i]
        prev_o = min(o_lows, key=lambda x: abs(x - prev_p)) if o_lows else None
        curr_o = min(o_lows, key=lambda x: abs(x - curr_p)) if o_lows else None
        if prev_o is None or curr_o is None:
            continue
        if (price.iloc[curr_p] < price.iloc[prev_p] and
                oscillator.iloc[curr_o] > oscillator.iloc[prev_o]):
            bullish.append((curr_p, curr_o))

    return bearish, bullish


# =============================================================================
# DEMO: small numerical examples used in the Obsidian notes
# =============================================================================
if __name__ == "__main__":
    # ------------- Numerical example for Momentum & ROC -------------
    sample = pd.Series([50, 51, 53, 52, 54, 55, 57, 56, 58, 60, 62])
    print("Sample closes:", sample.tolist())
    print("10-day Momentum:", momentum(sample, 10).iloc[-1])   # 62 - 50 = 12
    print("10-day ROC ratio:", rate_of_change(sample, 10).iloc[-1])  # 62/50 = 1.24
    print("10-day ROC %:", rate_of_change_pct(sample, 10).iloc[-1])  # 24%
    print()

    # ------------- Build a longer synthetic series for charts -------------
    df = generate_synthetic_prices()
    df['high'] = df['close'] * (1 + np.random.uniform(0, 0.015, len(df)))
    df['low'] = df['close'] * (1 - np.random.uniform(0, 0.015, len(df)))

    df['mom_10'] = momentum(df['close'], 10)
    df['roc_10'] = rate_of_change(df['close'], 10)
    df['ma_osc'] = ma_oscillator(df['close'], 20)
    df['price_osc'] = price_oscillator(df['close'], 10, 20)
    df['macd'], df['signal'], df['hist'] = macd(df['close'])
    df['rsi_14'] = rsi(df['close'], 14)
    df['k'], df['d'] = stochastic(df['high'], df['low'], df['close'])
    df['slow_k'], df['slow_d'] = slow_stochastic(df['high'], df['low'], df['close'])

    print(df[['close', 'mom_10', 'roc_10', 'rsi_14', 'macd', 'slow_k']].tail())
