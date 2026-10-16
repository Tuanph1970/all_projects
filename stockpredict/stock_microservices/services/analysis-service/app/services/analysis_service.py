"""Analysis Service - Technical & Fundamental Analysis"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import httpx
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repositories.analysis_repository import AnalysisRepository
from app.models.domain import AnalysisType
from app.models.schemas import (
    TechnicalAnalysisResponse, TechnicalIndicator, SignalType,
    FundamentalAnalysisResponse, FundamentalMetric,
    ScreenerResponse, ScreenerStock, ScreenerFilter,
    CurrentPriceData, MovingAverages, TradingAnalysis, ChartData,
    MomentumIndicators, VolatilityIndicators, VolumeIndicators,
    SupportResistance, TradingSignal,
    CompanyInfo, ValuationSummary, ValuationFactor, FinancialRatios,
    GrowthMetrics, IncomeStatement, BalanceSheet, CashFlow,
    AtrPoint, AtrResponse, SwingType, SwingPivot, SwingsResponse,
    SRLevelType, SRTouch, SRLevel, SRBreak, SRResponse,
    Regime, RegimeFeatures, RegimeResponse,
)
from app.services.sr_volume import (
    aggregate_level_volume,
    detect_attacks,
    detect_breaks,
    effective_level_type,
    level_price_cog,
    repelled_attacks,
    trailing_atr,
)

settings = get_settings()
logger = logging.getLogger(__name__)

# `period` is a bar count in the UI, but the history API takes a date range.
# The VN market trades ~5 of every 7 calendar days, minus holidays, so ask for
# a little over 1.5 calendar days per requested bar.
CALENDAR_DAYS_PER_BAR = 1.6

# Extra bars fetched *before* the displayed window so the slowest indicator
# (SMA 200) has a full window at the first displayed bar instead of NaN.
INDICATOR_WARMUP_BARS = 200


class AnalysisService:
    def __init__(self, session: AsyncSession):
        self.repo = AnalysisRepository(session)
        self.session = session

    async def _fetch_historical_data(self, symbol: str, days: int = 100) -> Optional[pd.DataFrame]:
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}/api/v2/stocks/{symbol}/history",
                    params={"start_date": start_date, "end_date": end_date},
                    timeout=60.0
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data"):
                        df = pd.DataFrame(data["data"])
                        df["date"] = pd.to_datetime(df["date"])
                        return df.sort_values("date")
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
        return None

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

    def _calculate_macd(self, prices: pd.Series) -> tuple:
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        return float(macd.iloc[-1]), float(signal.iloc[-1])

    def _calculate_bollinger(self, prices: pd.Series, period: int = 20) -> tuple:
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        return float(upper.iloc[-1]), float(lower.iloc[-1]), float(sma.iloc[-1])

    def _calculate_atr(self, ohlc: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range (Wilder's RMA smoothing).

        Returns the full ATR series indexed identically to `ohlc` so callers
        can align it with their bars; consumers wanting only the latest value
        read `.iloc[-1]`. Used by the trader-decision helper for swing stops
        and volatility-adjusted sizing (Schwager Ch 9, 16).
        """
        high = ohlc["high"].astype(float)
        low = ohlc["low"].astype(float)
        close = ohlc["close"].astype(float)
        prev_close = close.shift(1)
        tr = pd.concat(
            [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1,
        ).max(axis=1)
        # Wilder's smoothing == EMA with alpha = 1/period.
        return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    @staticmethod
    def _safe_float(value: Any, digits: int = 2) -> Optional[float]:
        """Round to `digits`, or return None for NaN/inf/missing.

        Indicator windows produce NaN until they are filled, and NaN is not
        valid JSON — it must reach the client as null so the UI can show N/A
        for a genuinely uncomputable value rather than failing the response.
        """
        if value is None:
            return None
        try:
            f = float(value)
        except (TypeError, ValueError):
            return None
        if not np.isfinite(f):
            return None
        return round(f, digits)

    def _calculate_stochastic(self, ohlc: pd.DataFrame, k_period: int = 14,
                              d_period: int = 3) -> tuple:
        """Stochastic oscillator %K / %D from the high/low/close bar.

        %K is the close's position inside the `k_period` high-low range;
        %D is its `d_period` simple moving average. Returns the latest pair.
        """
        high = ohlc["high"].astype(float).rolling(window=k_period).max()
        low = ohlc["low"].astype(float).rolling(window=k_period).min()
        close = ohlc["close"].astype(float)
        span = high - low
        # A flat range would divide by zero; treat it as mid-range (50).
        k = ((close - low) / span.replace(0, np.nan) * 100).fillna(50.0)
        d = k.rolling(window=d_period).mean()
        return float(k.iloc[-1]), float(d.iloc[-1]) if not pd.isna(d.iloc[-1]) else float(k.iloc[-1])

    def _calculate_obv(self, ohlc: pd.DataFrame) -> float:
        """On-Balance Volume accumulated over the supplied window.

        Volume is added on an up close and subtracted on a down close, so the
        absolute level is only meaningful relative to the start of the window
        — which is why this runs on the displayed bars, matching the chart.
        """
        close = ohlc["close"].astype(float)
        volume = ohlc["volume"].astype(float)
        direction = np.sign(close.diff()).fillna(0.0)
        return float((direction * volume).sum())

    def _calculate_fibonacci_levels(self, ohlc: pd.DataFrame) -> Dict[str, float]:
        """Retracement levels between the window's extreme low and high.

        Keys are the retracement percentages; values run from the high (0%)
        down to the low (100%) when the window's high came last, and are
        mirrored when the low came last, so 0% is always the swing origin.
        """
        high = float(ohlc["high"].astype(float).max())
        low = float(ohlc["low"].astype(float).min())
        span = high - low
        if span <= 0:
            return {}
        ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        high_is_last = ohlc["high"].astype(float).idxmax() > ohlc["low"].astype(float).idxmin()
        levels: Dict[str, float] = {}
        for r in ratios:
            # Uptrend swing (low then high): retrace down from the high.
            # Downtrend swing (high then low): retrace up from the low.
            price = high - span * r if high_is_last else low + span * r
            levels[f"{r * 100:.1f}%"] = round(price, 2)
        return levels

    def _find_swing_pivots(self, ohlc: pd.DataFrame, window: int = 3) -> List[SwingPivot]:
        """Fractal swing pivots over a rolling window of `window` bars each side.

        A bar at index i is a swing high iff its high is strictly greater than
        the highs of the `window` bars on either side; symmetric for swing low.
        Deterministic across reruns; returns pivots in chronological order.
        """
        if window < 1 or len(ohlc) < 2 * window + 1:
            return []
        highs = ohlc["high"].astype(float).values
        lows = ohlc["low"].astype(float).values
        dates = ohlc["date"].dt.strftime("%Y-%m-%d").tolist() if "date" in ohlc.columns else [str(i) for i in range(len(ohlc))]

        pivots: List[SwingPivot] = []
        for i in range(window, len(ohlc) - window):
            left = slice(i - window, i)
            right = slice(i + 1, i + 1 + window)
            if highs[i] > highs[left].max() and highs[i] > highs[right].max():
                pivots.append(SwingPivot(
                    bar_index=i, date=dates[i], type=SwingType.HIGH, price=float(highs[i])
                ))
            if lows[i] < lows[left].min() and lows[i] < lows[right].min():
                pivots.append(SwingPivot(
                    bar_index=i, date=dates[i], type=SwingType.LOW, price=float(lows[i])
                ))
        return pivots

    def _find_sr_levels(
        self,
        ohlc: pd.DataFrame,
        window: int = 3,
        tolerance_pct: float = 2.0,
    ) -> tuple:
        """Cluster swing pivots into typed S/R levels (Schwager Ch 4).

        Two pivots belong to the same level when their prices are within
        `tolerance_pct` percent of the running cluster mean. Each cluster
        emits a single `SRLevel` carrying mean price, dominant pivot type
        (support / resistance / flip on ties), strength (touch count) and
        age_bars (bars since the most recent touch).

        Each level also carries Edwards & Magee's two volume measures
        (EM-2 `FR-EM-S1`, `FR-EM-S2`): `volume_strength`, the volume transacted
        at the level relative to the symbol's own trailing volume, and
        `price_cog`, the volume-weighted centre of gravity of its congestion.
        Both are computed **per touch and then aggregated**, which `S1`
        measured to be the only informative shape — a cluster's touches are
        scattered across the whole window, so a single cluster-wide span is
        most of the frame and its relative volume collapses towards 1.0.

        `price` and `strength` are deliberately unchanged: three live consumers
        read them, and moving the level price is gated behind EM-2's `D1`
        evidence.

        Returns `(supports, resistances)` — both lists are sorted by price
        ascending; a FLIP level appears in both.
        """
        pivots = self._find_swing_pivots(ohlc, window=window)
        if not pivots:
            return [], []

        last_bar_index = len(ohlc) - 1
        sorted_pivots = sorted(pivots, key=lambda p: p.price)

        clusters: List[List[SwingPivot]] = [[sorted_pivots[0]]]
        for p in sorted_pivots[1:]:
            current = clusters[-1]
            mean = sum(x.price for x in current) / len(current)
            if mean > 0 and abs(p.price - mean) / mean * 100 <= tolerance_pct:
                current.append(p)
            else:
                clusters.append([p])

        # Computed once for the frame, not once per level: the ATR is a
        # property of the symbol's volatility, and recomputing it inside the
        # loop is a measurable regression on callers that build levels in bulk
        # (the H-S1 harness builds them thousands of times).
        try:
            level_atr = trailing_atr(ohlc)
        except Exception:  # noqa: BLE001
            level_atr = None

        levels: List[SRLevel] = []
        for cluster in clusters:
            prices = [p.price for p in cluster]
            bars = [p.bar_index for p in cluster]
            highs = sum(1 for p in cluster if p.type == SwingType.HIGH)
            lows = len(cluster) - highs
            if highs > lows:
                kind = SRLevelType.RESISTANCE
            elif lows > highs:
                kind = SRLevelType.SUPPORT
            else:
                kind = SRLevelType.FLIP
            level_price = round(sum(prices) / len(prices), 4)

            # EM-2: the volume measures are corroboration, never a
            # precondition for the level existing. Three consumers depend on
            # these levels being produced, so a failure anywhere in the volume
            # layer degrades to "unknown" and the level ships regardless.
            volume_strength: Optional[float] = None
            price_cog: Optional[float] = None
            try:
                measured = aggregate_level_volume(
                    ohlc, bars, level_price=level_price,
                )
                volume_strength = measured.value
                price_cog = level_price_cog(ohlc, bars, level_price=level_price)
            except Exception:  # noqa: BLE001 — a volume bug must not lose levels
                logger.warning(
                    "EM-2 volume measures failed for level at %s; "
                    "falling back to the touch count", level_price,
                    exc_info=True,
                )

            # FR-EM-S3: the level's break history, and the type it implies.
            # Scanned from the level's FIRST touch — a crossing that predates
            # the level is not a penetration of it.
            breaks: List[SRBreak] = []
            effective_type = kind
            attacks = 0
            try:
                breaks = detect_breaks(
                    ohlc, level_price, first_bar=min(bars), declared_type=kind,
                    atr=level_atr,
                )
                effective_type = effective_level_type(kind, breaks)
                attacks = repelled_attacks(detect_attacks(
                    ohlc, level_price, first_bar=min(bars), declared_type=kind,
                    atr=level_atr,
                ))
            except Exception:  # noqa: BLE001 — same rule as above
                logger.warning(
                    "EM-2 break detection failed for level at %s; "
                    "reporting no break history", level_price,
                    exc_info=True,
                )
                breaks = []
                effective_type = kind
                attacks = 0

            levels.append(SRLevel(
                price=level_price,
                type=kind,
                strength=len(cluster),
                age_bars=last_bar_index - max(bars),
                touches=[
                    SRTouch(
                        bar_index=p.bar_index, date=p.date,
                        price=p.price, pivot_type=p.type,
                    ) for p in cluster
                ],
                volume_strength=volume_strength,
                price_cog=price_cog,
                breaks=breaks,
                effective_type=effective_type,
                role_reversed=effective_type != kind,
                attacks=attacks,
            ))

        supports = [lv for lv in levels if lv.type in (SRLevelType.SUPPORT, SRLevelType.FLIP)]
        resistances = [lv for lv in levels if lv.type in (SRLevelType.RESISTANCE, SRLevelType.FLIP)]
        return supports, resistances

    def _find_support_resistance(self, ohlc: pd.DataFrame, current_price: float,
                                 max_levels: int = 3) -> tuple:
        """Nearest support/resistance levels around `current_price`.

        Delegates the pivot detection and clustering to `_find_sr_levels`
        (F-003) and then splits the levels by where price actually is: a
        level below price supports it, one above resists it. Both lists come
        back ordered nearest-first, so index 0 is S1 / R1.
        """
        sr_supports, sr_resistances = self._find_sr_levels(ohlc)

        below = sorted(
            {lv.price for lv in sr_supports + sr_resistances if lv.price < current_price},
            reverse=True,
        )[:max_levels]
        above = sorted(
            {lv.price for lv in sr_supports + sr_resistances if lv.price > current_price}
        )[:max_levels]

        # A window with no pivot on one side (price at a new extreme) falls
        # back to that side's window extreme so the UI still has a level.
        if not below:
            low = float(ohlc["low"].astype(float).min())
            below = [low] if low < current_price else []
        if not above:
            high = float(ohlc["high"].astype(float).max())
            above = [high] if high > current_price else []

        return below, above

    def _determine_signal(self, rsi: float, macd: float, macd_signal: float,
                         current_price: float, sma_20: float, sma_50: float) -> tuple:
        score = 0

        # RSI signal
        if rsi < 30:
            score += 30
        elif rsi < 40:
            score += 15
        elif rsi > 70:
            score -= 30
        elif rsi > 60:
            score -= 15

        # MACD signal
        if macd > macd_signal:
            score += 20
        else:
            score -= 20

        # Price vs SMA
        if current_price > sma_20:
            score += 15
        else:
            score -= 15

        if current_price > sma_50:
            score += 15
        else:
            score -= 15

        # Determine signal type
        if score >= 50:
            signal = SignalType.STRONG_BUY
        elif score >= 20:
            signal = SignalType.BUY
        elif score <= -50:
            signal = SignalType.STRONG_SELL
        elif score <= -20:
            signal = SignalType.SELL
        else:
            signal = SignalType.HOLD

        strength = min(1.0, max(0.0, (abs(score) / 100)))
        return signal, strength, score

    async def get_technical_analysis(self, symbol: str, period: int = 100) -> Optional[TechnicalAnalysisResponse]:
        # Cache is intentionally skipped here: the old cache was keyed only by
        # symbol (no period), so it returned chart_data=None for every period
        # change after the first load, making the chart go blank.  The
        # save_analysis call below still runs so portfolio/screener features
        # continue to get updated metrics.
        #
        # `period` is the number of bars the caller wants to SEE.  Fetch a
        # warm-up run ahead of it as well, otherwise every long-window
        # indicator (SMA 200 above all) is NaN and reaches the UI as N/A.
        lookback_days = int((period + INDICATOR_WARMUP_BARS) * CALENDAR_DAYS_PER_BAR)
        full = await self._fetch_historical_data(symbol, lookback_days)
        if full is None or len(full) < 20:
            return None

        # Warm-up bars feed the indicators but are not shown; everything that
        # describes "the window" (chart, S/R, Fibonacci, volatility, OBV) is
        # measured on the displayed bars only.
        df = full.tail(period).reset_index(drop=True)

        full_prices = full["close"].astype(float)
        prices = df["close"].astype(float)
        current_price = float(prices.iloc[-1])

        # Calculate indicators — momentum and moving averages read the full
        # series so their windows are complete at the last bar.
        rsi = self._calculate_rsi(full_prices)
        macd, macd_signal = self._calculate_macd(full_prices)
        bb_upper, bb_lower, bb_middle = self._calculate_bollinger(full_prices)
        stoch_k, stoch_d = self._calculate_stochastic(full)
        atr = float(self._calculate_atr(full).iloc[-1]) if len(full) > 14 else float("nan")
        sma_20 = float(full_prices.rolling(20).mean().iloc[-1])
        sma_50 = float(full_prices.rolling(50).mean().iloc[-1]) if len(full_prices) >= 50 else sma_20
        supports, resistances = self._find_support_resistance(df, current_price)

        signal, strength, score = self._determine_signal(rsi, macd, macd_signal, current_price, sma_20, sma_50)

        # Determine trend
        if current_price > sma_20 > sma_50:
            trend = "bullish"
        elif current_price < sma_20 < sma_50:
            trend = "bearish"
        else:
            trend = "neutral"

        # Calculate volatility
        volatility_val = float(prices.pct_change().std() * 100)
        if volatility_val < 1.5:
            volatility = "low"
        elif volatility_val > 3:
            volatility = "high"
        else:
            volatility = "medium"

        indicators = [
            TechnicalIndicator(name="RSI", value=round(rsi, 2),
                             signal="oversold" if rsi < 30 else ("overbought" if rsi > 70 else "neutral")),
            TechnicalIndicator(name="MACD", value=round(macd, 4),
                             signal="bullish" if macd > macd_signal else "bearish"),
            TechnicalIndicator(name="SMA 20", value=round(sma_20, 2),
                             signal="above" if current_price > sma_20 else "below"),
            TechnicalIndicator(name="SMA 50", value=round(sma_50, 2),
                             signal="above" if current_price > sma_50 else "below"),
            TechnicalIndicator(name="BB Upper", value=round(bb_upper, 2), signal="resistance"),
            TechnicalIndicator(name="BB Lower", value=round(bb_lower, 2), signal="support"),
        ]

        # Cache result.  This write only feeds portfolio/screener; the response
        # below is already fully computed from price history, so a DB hiccup
        # (stale pooled connection after an idle gap, tunnel drop) must not
        # turn into a 500 that the Indicators tab renders as a wall of N/A.
        try:
            await self.repo.save_analysis(
                symbol=symbol,
                analysis_type=AnalysisType.TECHNICAL,
                rsi=rsi,
                macd=macd,
                macd_signal=macd_signal,
                sma_20=sma_20,
                sma_50=sma_50,
                bollinger_upper=bb_upper,
                bollinger_lower=bb_lower,
                overall_signal=signal.value,
                signal_strength=strength,
                technical_score=score,
                support_levels=supports,
                resistance_levels=resistances
            )
        except Exception as exc:  # noqa: BLE001 - best-effort cache write
            logger.warning("save_analysis failed for %s (serving uncached): %s", symbol, exc)
            try:
                await self.repo.session.rollback()
            except Exception:  # noqa: BLE001 - connection may already be gone
                pass

        # Get latest OHLCV data
        latest_row = df.iloc[-1]
        open_price = float(latest_row.get("open", current_price)) if "open" in df.columns else None
        high_price = float(latest_row.get("high", current_price)) if "high" in df.columns else None
        low_price = float(latest_row.get("low", current_price)) if "low" in df.columns else None
        volume = int(latest_row.get("volume", 0)) if "volume" in df.columns else None

        # Calculate change
        if len(df) >= 2:
            prev_close = float(df.iloc[-2]["close"])
            change = current_price - prev_close
            change_percent = (change / prev_close) * 100 if prev_close != 0 else 0
        else:
            change = None
            change_percent = None

        # Calculate additional moving averages
        sma_200 = float(full_prices.rolling(200).mean().iloc[-1]) if len(full_prices) >= 200 else None
        ema_12 = float(full_prices.ewm(span=12).mean().iloc[-1])
        ema_26 = float(full_prices.ewm(span=26).mean().iloc[-1])

        # Volume measures over the displayed window
        volumes = df["volume"].astype(float) if "volume" in df.columns else pd.Series(dtype=float)
        volume_avg_20 = float(volumes.rolling(20).mean().iloc[-1]) if len(volumes) >= 20 else None
        obv = self._calculate_obv(df) if len(volumes) else None
        volume_ratio = (
            float(volumes.iloc[-1]) / volume_avg_20
            if volume_avg_20 else None
        )

        fibonacci_levels = self._calculate_fibonacci_levels(df)

        # Build chart data
        chart_data = ChartData(
            dates=[d.strftime("%Y-%m-%d") for d in df["date"].tolist()],
            prices=[float(p) for p in prices.tolist()],
            volumes=[int(v) for v in df["volume"].tolist()] if "volume" in df.columns else [],
            opens=[float(o) for o in df["open"].tolist()] if "open" in df.columns else [],
            highs=[float(h) for h in df["high"].tolist()] if "high" in df.columns else [],
            lows=[float(l) for l in df["low"].tolist()] if "low" in df.columns else []
        )

        # Build trading recommendation reasons
        reasons = []
        if rsi < 30:
            reasons.append("RSI indicates oversold conditions")
        elif rsi > 70:
            reasons.append("RSI indicates overbought conditions")
        if macd > macd_signal:
            reasons.append("MACD bullish crossover")
        else:
            reasons.append("MACD bearish crossover")
        if current_price > sma_20:
            reasons.append("Price above 20-day SMA")
        if current_price > sma_50:
            reasons.append("Price above 50-day SMA")

        signals = self._build_trading_signals(
            current_price=current_price,
            rsi=rsi, macd=macd, macd_signal=macd_signal,
            stoch_k=stoch_k, sma_20=sma_20, sma_50=sma_50, sma_200=sma_200,
            bb_upper=bb_upper, bb_lower=bb_lower,
            volume_ratio=volume_ratio, trend=trend,
        )

        return TechnicalAnalysisResponse(
            symbol=symbol.upper(),
            current_price=CurrentPriceData(
                price=round(current_price, 2),
                open=round(open_price, 2) if open_price else None,
                high=round(high_price, 2) if high_price else None,
                low=round(low_price, 2) if low_price else None,
                volume=volume,
                change=round(change, 2) if change else None,
                change_percent=round(change_percent, 2) if change_percent else None
            ),
            indicators=indicators,
            moving_averages=MovingAverages(
                SMA_20=self._safe_float(sma_20),
                SMA_50=self._safe_float(sma_50),
                SMA_200=self._safe_float(sma_200),
                EMA_12=self._safe_float(ema_12),
                EMA_26=self._safe_float(ema_26)
            ),
            momentum_indicators=MomentumIndicators(
                RSI=self._safe_float(rsi),
                MACD=self._safe_float(macd, 4),
                MACD_Signal=self._safe_float(macd_signal, 4),
                MACD_Histogram=self._safe_float(macd - macd_signal, 4),
                Stoch_K=self._safe_float(stoch_k),
                Stoch_D=self._safe_float(stoch_d),
            ),
            volatility_indicators=VolatilityIndicators(
                BB_Upper=self._safe_float(bb_upper),
                BB_Middle=self._safe_float(bb_middle),
                BB_Lower=self._safe_float(bb_lower),
                BB_Width=self._safe_float((bb_upper - bb_lower) / bb_middle * 100 if bb_middle else None),
                ATR=self._safe_float(atr),
                ATR_Percent=self._safe_float(atr / current_price * 100 if current_price else None),
            ),
            volume_indicators=VolumeIndicators(
                OBV=self._safe_float(obv, 0),
                volume_avg_20=self._safe_float(volume_avg_20, 0),
                volume_ratio=self._safe_float(volume_ratio),
            ),
            support_resistance=SupportResistance(
                support_levels=[round(s, 2) for s in supports],
                resistance_levels=[round(r, 2) for r in resistances],
            ),
            fibonacci_levels=fibonacci_levels,
            trading_analysis=TradingAnalysis(
                recommendation=signal.value.upper().replace("_", " "),
                score=float(score),
                confidence=round(strength, 2),
                reasons=reasons,
                signals=signals
            ),
            chart_data=chart_data,
            overall_signal=signal,
            signal_strength=strength,
            technical_score=score,
            support_levels=[round(s, 2) for s in supports],
            resistance_levels=[round(r, 2) for r in resistances],
            trend=trend,
            volatility=volatility,
            generated_at=datetime.now()
        )

    def _build_trading_signals(self, current_price: float, rsi: float, macd: float,
                               macd_signal: float, stoch_k: Optional[float],
                               sma_20: float, sma_50: float, sma_200: Optional[float],
                               bb_upper: float, bb_lower: float,
                               volume_ratio: Optional[float], trend: str) -> List[TradingSignal]:
        """Per-indicator verdicts backing the aggregate recommendation.

        Signal words are the ones the UI colours (BUY / SELL / NEUTRAL); an
        indicator with no computable value is omitted rather than reported
        as neutral, so a short history shows fewer rows instead of wrong ones.
        """
        def _ma_signal(name: str, level: Optional[float]) -> Optional[TradingSignal]:
            if level is None or not np.isfinite(level):
                return None
            return TradingSignal(
                indicator=name,
                signal="BUY" if current_price > level else "SELL",
                value=round(level, 2),
            )

        candidates: List[Optional[TradingSignal]] = [
            TradingSignal(
                indicator="RSI",
                signal="BUY" if rsi < 30 else ("SELL" if rsi > 70 else "NEUTRAL"),
                value=round(rsi, 2),
            ),
            TradingSignal(
                indicator="MACD",
                signal="BUY" if macd > macd_signal else "SELL",
                value=round(macd, 4),
            ),
            None if stoch_k is None or not np.isfinite(stoch_k) else TradingSignal(
                indicator="Stochastic",
                signal="BUY" if stoch_k < 20 else ("SELL" if stoch_k > 80 else "NEUTRAL"),
                value=round(stoch_k, 2),
            ),
            _ma_signal("SMA 20", sma_20),
            _ma_signal("SMA 50", sma_50),
            _ma_signal("SMA 200", sma_200),
            None if not np.isfinite(bb_upper) or not np.isfinite(bb_lower) else TradingSignal(
                indicator="Bollinger",
                signal=("BUY" if current_price <= bb_lower
                        else ("SELL" if current_price >= bb_upper else "NEUTRAL")),
                value=round(current_price, 2),
            ),
            None if volume_ratio is None else TradingSignal(
                indicator="Volume",
                signal="HIGH" if volume_ratio > 1.5 else ("LOW" if volume_ratio < 0.5 else "NORMAL"),
                value=round(volume_ratio, 2),
            ),
            TradingSignal(indicator="Trend", signal=trend.upper(), value=trend),
        ]
        return [c for c in candidates if c is not None]


    async def get_fundamental_analysis(self, symbol: str) -> Optional[FundamentalAnalysisResponse]:
        # Fetch fundamental data from stock-data-service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}/api/v2/companies/{symbol}/financials",
                    timeout=30.0
                )
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch financials for {symbol}: {response.status_code}")
                    return None

                data = response.json()

                # Build company info
                company_info = CompanyInfo(
                    name=data.get("company_name"),
                    marketCap=data.get("market_cap"),
                    industry=None,
                    sector=None,
                    exchange=None
                )

                # Calculate valuation score and build valuation summary
                score = self._calculate_fundamental_score(data)
                rating = "undervalued" if score > 70 else ("overvalued" if score < 40 else "fair")

                valuation_factors = []
                pe = data.get("pe_ratio")
                if pe is not None:
                    pe_status = "undervalued" if pe < 15 else ("overvalued" if pe > 25 else "fair")
                    valuation_factors.append(ValuationFactor(factor="P/E", value=f"{pe:.2f}", status=pe_status))

                pb = data.get("pb_ratio")
                if pb is not None:
                    pb_status = "undervalued" if pb < 1.5 else ("overvalued" if pb > 3 else "fair")
                    valuation_factors.append(ValuationFactor(factor="P/B", value=f"{pb:.2f}", status=pb_status))

                roe = data.get("roe")
                if roe is not None:
                    roe_status = "strong" if roe > 15 else ("weak" if roe < 5 else "fair")
                    valuation_factors.append(ValuationFactor(factor="ROE", value=f"{roe:.2f}%", status=roe_status))

                valuation_summary = ValuationSummary(
                    status=rating,
                    score=score,
                    factors=valuation_factors
                )

                # Get nested data from stock-data-service response
                fr_data = data.get("financial_ratios") or {}
                gm_data = data.get("growth_metrics") or {}
                is_data = data.get("income_statement") or {}
                bs_data = data.get("balance_sheet") or {}
                cf_data = data.get("cash_flow") or {}

                # Build financial ratios - use nested data if available, fallback to flat
                financial_ratios = FinancialRatios(
                    pe=fr_data.get("pe") or data.get("pe_ratio"),
                    pb=fr_data.get("pb") or data.get("pb_ratio"),
                    ps=fr_data.get("ps") or data.get("ps_ratio"),
                    roe=fr_data.get("roe") or data.get("roe"),
                    roa=fr_data.get("roa") or data.get("roa"),
                    debtToEquity=fr_data.get("debtToEquity") or data.get("debt_to_equity"),
                    currentRatio=fr_data.get("currentRatio") or data.get("current_ratio"),
                    quickRatio=fr_data.get("quickRatio") or data.get("quick_ratio"),
                    grossMargin=fr_data.get("grossMargin") or data.get("gross_margin"),
                    operatingMargin=fr_data.get("operatingMargin") or data.get("operating_margin"),
                    netMargin=fr_data.get("netMargin") or data.get("profit_margin")
                )

                # Build growth metrics
                growth_metrics = GrowthMetrics(
                    revenueGrowth=gm_data.get("revenueGrowth") or data.get("revenue_growth"),
                    earningsGrowth=gm_data.get("earningsGrowth") or data.get("earnings_growth"),
                    epsGrowth=gm_data.get("epsGrowth")
                )

                # Build income statement
                income_statement = IncomeStatement(
                    revenue=is_data.get("revenue"),
                    grossProfit=is_data.get("grossProfit"),
                    operatingIncome=is_data.get("operatingIncome"),
                    netIncome=is_data.get("netIncome"),
                    eps=is_data.get("eps") or data.get("eps")
                )

                # Build balance sheet
                balance_sheet = BalanceSheet(
                    totalAssets=bs_data.get("totalAssets"),
                    totalLiabilities=bs_data.get("totalLiabilities"),
                    totalEquity=bs_data.get("totalEquity"),
                    cash=bs_data.get("cash"),
                    longTermDebt=bs_data.get("longTermDebt")
                )

                # Build cash flow
                cash_flow = CashFlow(
                    operatingCashFlow=cf_data.get("operatingCashFlow"),
                    investingCashFlow=cf_data.get("investingCashFlow"),
                    financingCashFlow=cf_data.get("financingCashFlow"),
                    freeCashFlow=cf_data.get("freeCashFlow"),
                    netCashFlow=cf_data.get("netCashFlow")
                )

                return FundamentalAnalysisResponse(
                    symbol=symbol.upper(),
                    company_name=data.get("company_name"),
                    company_info=company_info,
                    valuation_summary=valuation_summary,
                    financial_ratios=financial_ratios,
                    growth_metrics=growth_metrics,
                    income_statement=income_statement,
                    balance_sheet=balance_sheet,
                    cash_flow=cash_flow,
                    fundamental_score=score,
                    overall_rating=rating,
                    generated_at=datetime.now()
                )
        except Exception as e:
            logger.error(f"Fundamental analysis failed for {symbol}: {e}")
            return None

    def _rate_pe(self, pe: Optional[float]) -> Optional[str]:
        if pe is None:
            return None
        if pe < 10:
            return "undervalued"
        elif pe > 25:
            return "overvalued"
        return "fair"

    def _rate_roe(self, roe: Optional[float]) -> Optional[str]:
        if roe is None:
            return None
        if roe > 15:
            return "good"
        elif roe < 5:
            return "poor"
        return "average"

    def _calculate_fundamental_score(self, data: dict) -> float:
        score = 50
        if data.get("pe_ratio"):
            if data["pe_ratio"] < 15:
                score += 15
            elif data["pe_ratio"] > 30:
                score -= 15
        if data.get("roe"):
            if data["roe"] > 15:
                score += 15
            elif data["roe"] < 5:
                score -= 10
        if data.get("debt_to_equity"):
            if data["debt_to_equity"] < 0.5:
                score += 10
            elif data["debt_to_equity"] > 2:
                score -= 10
        return max(0, min(100, score))

    async def run_screener(self, filters: List[ScreenerFilter], sort_by: str = "symbol",
                          sort_order: str = "asc", limit: int = 50, offset: int = 0) -> ScreenerResponse:
        # Check cache
        filter_dicts = [f.model_dump() for f in filters]
        cached = await self.repo.get_cached_screener(filter_dicts)
        if cached:
            stocks = [ScreenerStock(**s) for s in cached.results[offset:offset + limit]]
            return ScreenerResponse(total=cached.total_matches, stocks=stocks, generated_at=cached.created_at)

        # Fetch stocks from stock-data-service priceboards endpoint
        try:
            async with httpx.AsyncClient() as client:
                # Get data from multiple stock groups for comprehensive coverage
                all_stocks = []
                groups = ["VN30", "VN100", "HOSE", "HNX"]

                for group in groups:
                    response = await client.get(
                        f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}/api/v2/priceboards",
                        params={"group": group},
                        timeout=60.0
                    )
                    if response.status_code == 200:
                        group_stocks = response.json()
                        if isinstance(group_stocks, list):
                            all_stocks.extend(group_stocks)

                # Remove duplicates by symbol
                seen_symbols = set()
                # Map exchange codes to standard names
                exchange_map = {"HSX": "HOSE", "HNX": "HNX", "UPCOM": "UPCOM"}

                stocks_data = []
                for stock in all_stocks:
                    symbol = stock.get("symbol")
                    if symbol and symbol not in seen_symbols:
                        seen_symbols.add(symbol)
                        # Map priceboards fields to screener fields
                        raw_exchange = stock.get("exchange", "")
                        mapped_exchange = exchange_map.get(raw_exchange, raw_exchange)
                        stocks_data.append({
                            "symbol": symbol,
                            "name": stock.get("name", symbol),
                            "price": stock.get("matchPrice", 0),
                            "change_percent": stock.get("changePercent", 0),
                            "volume": stock.get("totalQty", 0),
                            "market_cap": stock.get("market_cap"),
                            "exchange": mapped_exchange,
                            "pe_ratio": stock.get("pe_ratio"),
                            "rsi": stock.get("rsi"),
                            "signal": stock.get("signal")
                        })

                if not stocks_data:
                    logger.warning("No stocks data fetched from priceboards")
                    return ScreenerResponse(total=0, stocks=[], generated_at=datetime.now())

                # Apply filters
                filtered = self._apply_filters(stocks_data, filters)

                # Sort
                reverse = sort_order == "desc"
                filtered.sort(key=lambda x: x.get(sort_by, 0) or 0, reverse=reverse)

                # Cache results
                await self.repo.cache_screener_results(filter_dicts, filtered, len(filtered))

                # Paginate
                paginated = filtered[offset:offset + limit]
                stocks = [ScreenerStock(
                    symbol=s.get("symbol", ""),
                    name=s.get("name"),
                    exchange=s.get("exchange"),
                    price=s.get("price", 0),
                    change_percent=s.get("change_percent", 0),
                    volume=s.get("volume", 0),
                    market_cap=s.get("market_cap"),
                    pe_ratio=s.get("pe_ratio"),
                    rsi=s.get("rsi"),
                    signal=s.get("signal")
                ) for s in paginated]

                return ScreenerResponse(total=len(filtered), stocks=stocks, generated_at=datetime.now())
        except Exception as e:
            logger.error(f"Screener failed: {e}")
            return ScreenerResponse(total=0, stocks=[], generated_at=datetime.now())

    def _apply_filters(self, stocks: List[dict], filters: List[ScreenerFilter]) -> List[dict]:
        result = stocks
        for f in filters:
            result = [s for s in result if self._match_filter(s, f)]
        return result

    def _match_filter(self, stock: dict, filter: ScreenerFilter) -> bool:
        value = stock.get(filter.field)
        if value is None:
            return False

        if filter.operator.value == "gt":
            return value > filter.value
        elif filter.operator.value == "gte":
            return value >= filter.value
        elif filter.operator.value == "lt":
            return value < filter.value
        elif filter.operator.value == "lte":
            return value <= filter.value
        elif filter.operator.value == "eq":
            return value == filter.value
        elif filter.operator.value == "between":
            return filter.value <= value <= filter.value2
        return True

    # ------------------------------------------------------------------
    # Trader-helper foundations — F-001 (ATR), F-002 (swing pivots).
    # Consumed by decision-helper-service for stops / regime / S/R.
    # ------------------------------------------------------------------
    async def get_atr(self, symbol: str, period: int = 14, days: int = 100,
                      tail: int = 60) -> Optional[AtrResponse]:
        df = await self._fetch_historical_data(symbol, days)
        if df is None or len(df) < period + 1:
            return None
        if not {"high", "low", "close"}.issubset(df.columns):
            return None

        atr = self._calculate_atr(df, period=period).dropna()
        if atr.empty:
            return None

        recent = atr.tail(tail)
        dates = df["date"].dt.strftime("%Y-%m-%d").reindex(recent.index)
        series = [
            AtrPoint(date=d, atr=round(float(v), 6))
            for d, v in zip(dates.tolist(), recent.tolist())
        ]
        return AtrResponse(
            symbol=symbol.upper(),
            period=period,
            latest=round(float(atr.iloc[-1]), 6),
            series=series,
            generated_at=datetime.utcnow(),
        )

    async def get_swing_pivots(self, symbol: str, window: int = 3,
                               days: int = 200) -> Optional[SwingsResponse]:
        df = await self._fetch_historical_data(symbol, days)
        if df is None or len(df) < 2 * window + 1:
            return None
        if not {"high", "low"}.issubset(df.columns):
            return None

        pivots = self._find_swing_pivots(df, window=window)
        return SwingsResponse(
            symbol=symbol.upper(),
            window=window,
            pivots=pivots,
            generated_at=datetime.utcnow(),
        )

    async def get_sr_levels(
        self,
        symbol: str,
        window: int = 3,
        tolerance_pct: float = 2.0,
        days: int = 200,
    ) -> Optional[SRResponse]:
        df = await self._fetch_historical_data(symbol, days)
        if df is None or len(df) < 2 * window + 1:
            return None
        if not {"high", "low"}.issubset(df.columns):
            return None

        supports, resistances = self._find_sr_levels(
            df, window=window, tolerance_pct=tolerance_pct,
        )
        return SRResponse(
            symbol=symbol.upper(),
            window=window,
            tolerance_pct=tolerance_pct,
            supports=supports,
            resistances=resistances,
            generated_at=datetime.utcnow(),
        )

    # ------------------------------------------------------------------
    # F-004 — Regime feature vector (Schwager Ch 3, 4).
    # Aggregates long-MA slope, swing-structure count, ADX, and an
    # ATR-normalised band width, then classifies the bar as TREND /
    # RANGE / UNDEFINED. Consumed by decision-helper-service to branch
    # between trend-following and range-trading signal generators.
    # ------------------------------------------------------------------
    def _calculate_adx(self, ohlc: pd.DataFrame, period: int = 14) -> float:
        """Wilder ADX(14) — latest value (0..100). 0.0 when uncomputable."""
        from ta.trend import ADXIndicator
        adx = ADXIndicator(
            high=ohlc["high"].astype(float),
            low=ohlc["low"].astype(float),
            close=ohlc["close"].astype(float),
            window=period,
            fillna=False,
        ).adx()
        if adx.empty or pd.isna(adx.iloc[-1]):
            return 0.0
        return float(adx.iloc[-1])

    def _calculate_ma_slope(self, prices: pd.Series, ma_window: int = 50,
                            lookback: int = 20) -> float:
        """Long-MA slope as a per-bar fractional change.

        Returns (MA[t] - MA[t-lookback]) / MA[t-lookback] / lookback —
        i.e. average fractional rise per bar over the lookback window.
        Normalising by price keeps the threshold comparable across symbols.
        """
        if len(prices) < ma_window + lookback:
            return 0.0
        ma = prices.rolling(window=ma_window).mean()
        last = ma.iloc[-1]
        past = ma.iloc[-1 - lookback]
        if pd.isna(last) or pd.isna(past) or past == 0:
            return 0.0
        return float((last - past) / past / lookback)

    def _count_hh_hl(self, pivots: List[SwingPivot]) -> int:
        """Net trend-structure score from a list of swing pivots (Ch 3).

        +1 for each higher-high or higher-low (uptrend evidence),
        -1 for each lower-high or lower-low (downtrend evidence).
        The sign agrees with the dominant trend direction; magnitude
        reflects how consistently the structure holds.
        """
        if len(pivots) < 2:
            return 0
        score = 0
        last_high = None
        last_low = None
        for p in pivots:
            if p.type == SwingType.HIGH:
                if last_high is not None:
                    score += 1 if p.price > last_high else -1
                last_high = p.price
            else:
                if last_low is not None:
                    score += 1 if p.price > last_low else -1
                last_low = p.price
        return score

    def _range_atr_ratio(self, ohlc: pd.DataFrame, atr: float,
                         lookback: int = 20) -> float:
        """Recent (high-low) band measured in ATRs.

        For a clean trend the band grows linearly with bars (≈ lookback);
        for a sideways range the band stays modest (a few ATRs). Used
        together with slope and ADX — a small ratio with flat slope is
        the canonical RANGE signature.
        """
        if atr <= 0 or len(ohlc) < lookback:
            return 0.0
        window = ohlc.tail(lookback)
        band = float(window["high"].max() - window["low"].min())
        return band / atr

    def _classify_regime(
        self,
        features: RegimeFeatures,
        slope_threshold: float = 0.001,    # ~0.1% per bar (~2% over 20 bars)
        adx_threshold: float = 20.0,
        band_threshold: float = 12.0,      # 12 ATRs over a 20-bar window
    ) -> tuple:
        """Decision rules per road-map F-004.

        TREND     : strong directional slope, ADX above threshold,
                    and the HH/HL structure agrees with slope direction.
        RANGE     : flat slope, ADX below threshold, and the recent band
                    is narrow relative to ATR (price oscillating, not
                    extending).
        UNDEFINED : conflicting signals — caller should fall back to WAIT.
        """
        abs_slope = abs(features.slope)
        # Absence of swing pivots (hh_hl_count == 0) is treated as "no
        # evidence" rather than disagreement — tight clean trends often
        # have few confirmed fractals. Only an actively opposing count
        # vetoes the trend rule.
        trend_dir_matches = (
            features.hh_hl_count == 0
            or (features.slope > 0 and features.hh_hl_count > 0)
            or (features.slope < 0 and features.hh_hl_count < 0)
        )

        if (abs_slope > slope_threshold
                and features.adx > adx_threshold
                and trend_dir_matches):
            slope_score = min(abs_slope / (slope_threshold * 3), 1.0)
            adx_score = min((features.adx - adx_threshold) / 30.0, 1.0)
            struct_score = min(abs(features.hh_hl_count) / 4.0, 1.0)
            confidence = (slope_score + adx_score + struct_score) / 3.0
            return Regime.TREND, round(max(0.0, min(1.0, confidence)), 4)

        if (abs_slope <= slope_threshold
                and features.adx <= adx_threshold
                and features.range_atr_ratio < band_threshold):
            slope_score = 1.0 - min(abs_slope / slope_threshold, 1.0)
            adx_score = 1.0 - min(features.adx / adx_threshold, 1.0)
            band_score = 1.0 - min(features.range_atr_ratio / band_threshold, 1.0)
            confidence = (slope_score + adx_score + band_score) / 3.0
            return Regime.RANGE, round(max(0.0, min(1.0, confidence)), 4)

        return Regime.UNDEFINED, 0.0

    async def get_regime(
        self,
        symbol: str,
        days: int = 200,
        ma_window: int = 50,
        lookback: int = 20,
        swing_window: int = 3,
    ) -> Optional[RegimeResponse]:
        df = await self._fetch_historical_data(symbol, days)
        if df is None or len(df) < ma_window + lookback:
            return None
        if not {"high", "low", "close"}.issubset(df.columns):
            return None

        prices = df["close"].astype(float)

        slope = self._calculate_ma_slope(prices, ma_window=ma_window, lookback=lookback)
        pivots = self._find_swing_pivots(df, window=swing_window)
        # Cap to the most recent 12 confirmed pivots so older structure
        # doesn't drown out the current regime.
        recent_pivots = pivots[-12:] if len(pivots) > 12 else pivots
        hh_hl = self._count_hh_hl(recent_pivots)
        adx = self._calculate_adx(df, period=14)
        atr_series = self._calculate_atr(df, period=14).dropna()
        latest_atr = float(atr_series.iloc[-1]) if not atr_series.empty else 0.0
        band_ratio = self._range_atr_ratio(df, atr=latest_atr, lookback=lookback)

        features = RegimeFeatures(
            slope=round(slope, 6),
            hh_hl_count=hh_hl,
            adx=round(adx, 4),
            range_atr_ratio=round(band_ratio, 4),
        )
        regime, confidence = self._classify_regime(features)
        return RegimeResponse(
            symbol=symbol.upper(),
            regime=regime,
            confidence=confidence,
            features=features,
            generated_at=datetime.utcnow(),
        )
