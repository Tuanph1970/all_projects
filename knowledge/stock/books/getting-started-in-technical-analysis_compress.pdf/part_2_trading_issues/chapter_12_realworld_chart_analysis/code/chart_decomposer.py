"""
chart_decomposer.py
===================
Decomposes an OHLC chart into a list of overlapping, multi-timeframe
pattern findings, then groups them by temporal confluence.

This is NOT a Fourier transform — chart patterns aren't an orthogonal
basis. It's closer to multi-scale object detection: the same bars can
simultaneously be inside a flag, a trading range, and a bull trap, and
all three labels can be true.

Pipeline:
    Layer 1   resample to multiple timeframes
    Layer 2   run every detector on every timeframe
    Layer 3   collect raw findings (pattern, timeframe, span, confidence)
    Layer 4   cluster findings whose time-spans overlap → confluence groups
    Layer 5   score each group (count + weighted confidence)

Usage:
    from chart_decomposer import decompose_chart, summarize
    findings, groups = decompose_chart(df_daily)
    print(summarize(findings, groups))
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Callable, Iterable, Optional

import numpy as np
import pandas as pd

from chapter12_concepts import (
    detect_bull_trap,
    detect_bear_trap,
    detect_flag,
    counter_to_anticipated_breakout,
    wide_ranging_day,
    detect_island_reversal,
    spike_high,
    true_range,
)


# ==================================================================
# Data model
# ==================================================================
@dataclass
class Finding:
    """A single pattern occurrence located in time."""
    pattern: str
    timeframe: str
    start_idx: pd.Timestamp
    end_idx: pd.Timestamp
    confidence: float
    direction: str = ""           # 'bullish', 'bearish', or ''
    note: str = ""

    def overlaps(self, other: "Finding", tolerance_bars: int = 0,
                 freq: str = "D") -> bool:
        """True if the two findings' time spans intersect (with tolerance)."""
        tol = pd.Timedelta(tolerance_bars, unit=freq[0].lower() if freq else "D")
        return not (self.end_idx + tol < other.start_idx
                    or other.end_idx + tol < self.start_idx)


@dataclass
class ConfluenceGroup:
    """A bundle of findings whose spans overlap in time."""
    findings: list[Finding] = field(default_factory=list)
    bullish_score: float = 0.0
    bearish_score: float = 0.0

    @property
    def span_start(self) -> pd.Timestamp:
        return min(f.start_idx for f in self.findings)

    @property
    def span_end(self) -> pd.Timestamp:
        return max(f.end_idx for f in self.findings)

    @property
    def net_score(self) -> float:
        return self.bullish_score - self.bearish_score

    @property
    def conviction(self) -> str:
        n = len(self.findings)
        if n >= 4:
            return "very_high"
        if n == 3:
            return "high"
        if n == 2:
            return "moderate"
        return "low"


# ==================================================================
# Layer 1 — Multi-timeframe resampling
# ==================================================================
TF_RULES = {"D": "D", "W": "W-FRI", "M": "ME"}   # pandas freq codes


def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Standard OHLC resampling (open=first, high=max, low=min, close=last)."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    return df.resample(rule).agg(agg).dropna()


# ==================================================================
# Layer 2 — Detector adapters
# ==================================================================
# Each adapter wraps a Chapter-12 detector and returns list[Finding].
# Adapters share a common signature: (df, timeframe) -> list[Finding].

def _bars_to_index(df: pd.DataFrame, i: int) -> pd.Timestamp:
    return df.index[max(0, min(i, len(df) - 1))]


def adapter_bull_trap(df: pd.DataFrame, timeframe: str) -> list[Finding]:
    """Scan rolling windows for bull-trap setups."""
    out = []
    if len(df) < 30:
        return out
    # Use a rolling 30-bar window: range = high/low of first 20, breakout in next 10.
    for i in range(20, len(df) - 5):
        window = df.iloc[i - 20:i]
        rh = float(window["high"].max())
        rl = float(window["low"].min())
        flags = detect_bull_trap(df.iloc[i - 5:i + 10],
                                 range_high=rh, range_low=rl, lookforward=8)
        if flags.any():
            hit = flags.idxmax()
            out.append(Finding(
                pattern="bull_trap",
                timeframe=timeframe,
                start_idx=_bars_to_index(df, i - 5),
                end_idx=_bars_to_index(df, i + 8),
                confidence=0.7,
                direction="bearish",
                note=f"breakout above {rh:.2f} failed back into range",
            ))
    return _dedupe_by_time(out, gap_bars=10, freq=timeframe)


def adapter_bear_trap(df: pd.DataFrame, timeframe: str) -> list[Finding]:
    out = []
    if len(df) < 30:
        return out
    for i in range(20, len(df) - 5):
        window = df.iloc[i - 20:i]
        rh = float(window["high"].max())
        rl = float(window["low"].min())
        flags = detect_bear_trap(df.iloc[i - 5:i + 10],
                                 range_high=rh, range_low=rl, lookforward=8)
        if flags.any():
            out.append(Finding(
                pattern="bear_trap",
                timeframe=timeframe,
                start_idx=_bars_to_index(df, i - 5),
                end_idx=_bars_to_index(df, i + 8),
                confidence=0.7,
                direction="bullish",
                note=f"breakdown below {rl:.2f} failed back into range",
            ))
    return _dedupe_by_time(out, gap_bars=10, freq=timeframe)


def adapter_flag(df: pd.DataFrame, timeframe: str) -> list[Finding]:
    """Scan for flag/pennant setups across the series."""
    out = []
    pole_bars, flag_bars = 8, 8
    n = pole_bars + flag_bars
    for i in range(n, len(df)):
        sub = df.iloc[i - n:i]
        flag = detect_flag(sub, pole_bars=pole_bars, flag_bars=flag_bars)
        if flag is None:
            continue
        direction = "bullish" if flag["direction"] == "up" else "bearish"
        out.append(Finding(
            pattern="flag_pennant",
            timeframe=timeframe,
            start_idx=_bars_to_index(df, i - flag_bars),
            end_idx=_bars_to_index(df, i - 1),
            confidence=0.55,
            direction=direction,
            note=f"pole {flag['pole_size']:.2f}, flag [{flag['flag_low']:.2f}–"
                 f"{flag['flag_high']:.2f}]",
        ))
    return _dedupe_by_time(out, gap_bars=4, freq=timeframe)


def adapter_counter_breakout(df: pd.DataFrame, timeframe: str) -> list[Finding]:
    """Detect flags that broke out counter to the prior pole."""
    out = []
    pole_bars, flag_bars = 8, 8
    n = pole_bars + flag_bars
    for i in range(n + 2, len(df)):
        sub = df.iloc[i - n - 2:i - 2]
        flag = detect_flag(sub, pole_bars=pole_bars, flag_bars=flag_bars)
        if flag is None:
            continue
        latest_close = float(df.iloc[i - 1]["close"])
        signal = counter_to_anticipated_breakout(flag, latest_close)
        if signal is None:
            continue
        direction = "bullish" if signal == "counter_breakout_up" else "bearish"
        out.append(Finding(
            pattern="counter_to_anticipated_breakout",
            timeframe=timeframe,
            start_idx=_bars_to_index(df, i - flag_bars - 2),
            end_idx=_bars_to_index(df, i - 1),
            confidence=0.75,
            direction=direction,
            note=f"flag was {flag['direction']}, broke {signal.split('_')[-1]}",
        ))
    return _dedupe_by_time(out, gap_bars=4, freq=timeframe)


def adapter_wide_ranging_day(df: pd.DataFrame, timeframe: str) -> list[Finding]:
    flags = wide_ranging_day(df, lookback=14, k=2.0)
    out = []
    for ts, hit in flags.items():
        if not hit:
            continue
        bar = df.loc[ts]
        direction = "bullish" if bar["close"] > bar["open"] else "bearish"
        out.append(Finding(
            pattern="wide_ranging_day",
            timeframe=timeframe,
            start_idx=ts, end_idx=ts,
            confidence=0.5,
            direction=direction,
            note=f"TR {bar['high'] - bar['low']:.2f}",
        ))
    return out


def adapter_island_reversal(df: pd.DataFrame, timeframe: str) -> list[Finding]:
    flags = detect_island_reversal(df)
    out = []
    for ts, hit in flags.items():
        if not hit:
            continue
        out.append(Finding(
            pattern="island_reversal",
            timeframe=timeframe,
            start_idx=ts, end_idx=ts,
            confidence=0.8,
            direction="bearish",   # top island; mirror for bottom is left as ext.
            note="gap up + gap down isolating cluster",
        ))
    return out


def adapter_spike_high(df: pd.DataFrame, timeframe: str) -> list[Finding]:
    flags = spike_high(df, lookback=20, k=1.5)
    out = []
    for ts, hit in flags.items():
        if not hit:
            continue
        out.append(Finding(
            pattern="spike_high",
            timeframe=timeframe,
            start_idx=ts, end_idx=ts,
            confidence=0.45,
            direction="bearish",
            note="upper tail >1.5 ATR above prior close",
        ))
    return out


# Trend strength adapter — gives context to other findings
def adapter_trend(df: pd.DataFrame, timeframe: str,
                  lookback: int = 50) -> list[Finding]:
    """Crude trend tag using slope of the rolling mean."""
    if len(df) < lookback + 5:
        return []
    closes = df["close"]
    sma = closes.rolling(lookback).mean()
    slope = (sma.iloc[-1] - sma.iloc[-lookback // 2]) / (lookback // 2)
    atr = true_range(df).rolling(14).mean().iloc[-1]
    norm = slope / atr if atr else 0.0
    if abs(norm) < 0.05:
        direction, label = "", "ranging"
    elif norm > 0:
        direction, label = "bullish", "uptrend"
    else:
        direction, label = "bearish", "downtrend"
    return [Finding(
        pattern=f"trend_{label}",
        timeframe=timeframe,
        start_idx=df.index[-lookback],
        end_idx=df.index[-1],
        confidence=min(1.0, abs(norm)),
        direction=direction,
        note=f"normalized slope {norm:+.3f}",
    )]


DETECTORS: dict[str, Callable[[pd.DataFrame, str], list[Finding]]] = {
    "bull_trap":            adapter_bull_trap,
    "bear_trap":            adapter_bear_trap,
    "flag":                 adapter_flag,
    "counter_breakout":     adapter_counter_breakout,
    "wide_ranging_day":     adapter_wide_ranging_day,
    "island_reversal":      adapter_island_reversal,
    "spike_high":           adapter_spike_high,
    "trend":                adapter_trend,
}


# ==================================================================
# Helpers
# ==================================================================
def _dedupe_by_time(findings: list[Finding], gap_bars: int,
                    freq: str) -> list[Finding]:
    """Collapse adjacent firings of the *same* pattern within gap_bars."""
    if not findings:
        return findings
    findings = sorted(findings, key=lambda f: f.start_idx)
    keep = [findings[0]]
    delta = pd.Timedelta(gap_bars, unit="D")
    for f in findings[1:]:
        if f.start_idx - keep[-1].end_idx <= delta:
            # Extend the existing one rather than add a new one.
            keep[-1].end_idx = max(keep[-1].end_idx, f.end_idx)
            keep[-1].confidence = max(keep[-1].confidence, f.confidence)
        else:
            keep.append(f)
    return keep


# ==================================================================
# Layer 3-4 — Decompose + cluster
# ==================================================================
def decompose_chart(
    df: pd.DataFrame,
    timeframes: Iterable[str] = ("D", "W"),
    detectors: Optional[dict] = None,
) -> tuple[list[Finding], list[ConfluenceGroup]]:
    """
    Run every detector at every timeframe, then group findings whose
    time spans overlap.
    """
    detectors = detectors or DETECTORS
    findings: list[Finding] = []

    for tf in timeframes:
        if tf == "D":
            sub = df
        else:
            sub = resample_ohlc(df, TF_RULES[tf])
        for name, det in detectors.items():
            try:
                findings.extend(det(sub, tf))
            except Exception as e:                        # pragma: no cover
                print(f"  [warn] detector {name}@{tf} failed: {e}")

    findings.sort(key=lambda f: (f.start_idx, f.end_idx))
    groups = _cluster_overlapping(findings, tolerance_days=3)
    return findings, groups


def _cluster_overlapping(findings: list[Finding],
                         tolerance_days: int = 3) -> list[ConfluenceGroup]:
    """Greedy single-pass clustering by time overlap."""
    groups: list[ConfluenceGroup] = []
    tol = pd.Timedelta(tolerance_days, unit="D")

    for f in findings:
        placed = False
        for g in groups:
            if not (f.end_idx + tol < g.span_start or
                    g.span_end + tol < f.start_idx):
                g.findings.append(f)
                placed = True
                break
        if not placed:
            groups.append(ConfluenceGroup(findings=[f]))

    # Score each group
    for g in groups:
        for f in g.findings:
            if f.direction == "bullish":
                g.bullish_score += f.confidence
            elif f.direction == "bearish":
                g.bearish_score += f.confidence
    return groups


# ==================================================================
# Layer 5 — Reporting
# ==================================================================
def summarize(findings: list[Finding],
              groups: list[ConfluenceGroup],
              top_n: int = 5) -> str:
    """Human-readable text summary."""
    lines = []
    lines.append(f"Total findings: {len(findings)}")
    lines.append(f"Confluence groups: {len(groups)}")
    lines.append("")

    sorted_groups = sorted(
        groups, key=lambda g: (-len(g.findings), -abs(g.net_score))
    )

    lines.append(f"Top {min(top_n, len(sorted_groups))} confluence zones:")
    lines.append("-" * 76)
    for i, g in enumerate(sorted_groups[:top_n], 1):
        bias = "BULL" if g.net_score > 0 else ("BEAR" if g.net_score < 0 else "MIX")
        lines.append(
            f"\n[{i}] {g.span_start.date()} → {g.span_end.date()}  "
            f"({len(g.findings)} signals, conviction={g.conviction}, "
            f"bias={bias}, net={g.net_score:+.2f})"
        )
        for f in g.findings:
            arrow = {"bullish": "↑", "bearish": "↓"}.get(f.direction, "·")
            lines.append(
                f"    {arrow} [{f.timeframe}] {f.pattern:<32} "
                f"conf={f.confidence:.2f}  {f.note}"
            )
    return "\n".join(lines)


def to_dataframe(findings: list[Finding]) -> pd.DataFrame:
    """Flatten findings into a tidy DataFrame for further analysis."""
    return pd.DataFrame([asdict(f) for f in findings])


# ==================================================================
# Demo
# ==================================================================
if __name__ == "__main__":
    np.random.seed(7)

    # Synthetic 250-day series with a designed bull trap around day 180.
    n = 250
    dates = pd.date_range("2023-01-02", periods=n, freq="B")
    drift = np.concatenate([
        np.linspace(0.05, 0.12, 80),     # uptrend phase
        np.linspace(0.12, 0.05, 60),     # cooling
        np.array([0.40, 0.50, 0.30,      # spike to record highs
                  -0.30, -0.50, -0.60]), # immediate reversal — bull trap
        np.linspace(-0.10, -0.15, n - 80 - 60 - 6),
    ])
    noise = np.random.normal(0, 0.6, n)
    closes = 100 + np.cumsum(drift + noise)
    df = pd.DataFrame({
        "open":  closes + np.random.normal(0, 0.2, n),
        "high":  closes + np.abs(np.random.normal(0.4, 0.3, n)),
        "low":   closes - np.abs(np.random.normal(0.4, 0.3, n)),
        "close": closes,
    }, index=dates)

    findings, groups = decompose_chart(df, timeframes=("D", "W"))
    print(summarize(findings, groups, top_n=4))

    print("\n\nAll findings as DataFrame (first 12 rows):")
    print(to_dataframe(findings).head(12).to_string(index=False))
