"""
price_envelope.py
Price envelope bands (percent-of-MA) and Bollinger Bands (sigma-of-MA).

Schwager Ch. 4 introduces these as another way of mapping support and
resistance: an envelope around a moving average that contains most price
action. Touching the upper/lower band is interpreted as
overbought/oversold (note: Schwager warns this is unreliable in trends).
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class EnvelopeResult:
    ma: np.ndarray
    upper: np.ndarray
    lower: np.ndarray


def simple_moving_average(prices: np.ndarray, window: int) -> np.ndarray:
    prices = np.asarray(prices, dtype=float)
    out = np.full_like(prices, np.nan)
    if len(prices) < window:
        return out
    csum = np.cumsum(prices)
    out[window - 1] = csum[window - 1] / window
    out[window:] = (csum[window:] - csum[:-window]) / window
    return out


def percent_envelope(prices: np.ndarray, window: int = 20,
                     pct: float = 0.025) -> EnvelopeResult:
    """Upper = MA * (1 + pct); lower = MA * (1 - pct)."""
    ma = simple_moving_average(prices, window)
    return EnvelopeResult(ma=ma, upper=ma * (1 + pct), lower=ma * (1 - pct))


def bollinger_bands(prices: np.ndarray, window: int = 20,
                    num_std: float = 2.0) -> EnvelopeResult:
    """Bollinger: upper/lower = MA ± num_std * rolling_std."""
    prices = np.asarray(prices, dtype=float)
    ma = simple_moving_average(prices, window)
    std = np.full_like(prices, np.nan)
    for i in range(window - 1, len(prices)):
        std[i] = prices[i - window + 1:i + 1].std(ddof=0)
    return EnvelopeResult(ma=ma, upper=ma + num_std * std, lower=ma - num_std * std)


def envelope_signals(prices: np.ndarray, env: EnvelopeResult):
    """Return arrays of overbought/oversold flags."""
    return {
        'overbought': prices >= env.upper,
        'oversold':   prices <= env.lower,
    }


if __name__ == "__main__":
    np.random.seed(2)
    n = 100
    prices = 100 + np.cumsum(np.random.normal(0.05, 0.8, n))

    env = percent_envelope(prices, window=20, pct=0.025)
    bb = bollinger_bands(prices, window=20, num_std=2.0)

    flags = envelope_signals(prices, env)
    print(f"Overbought touches: {flags['overbought'].sum()}")
    print(f"Oversold touches:   {flags['oversold'].sum()}")
    print(f"Last price={prices[-1]:.2f}, MA={env.ma[-1]:.2f}, "
          f"env=[{env.lower[-1]:.2f}, {env.upper[-1]:.2f}], "
          f"BB=[{bb.lower[-1]:.2f}, {bb.upper[-1]:.2f}]")
