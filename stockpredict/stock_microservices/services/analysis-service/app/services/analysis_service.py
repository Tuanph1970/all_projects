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
    ScreenerResponse, ScreenerStock, ScreenerFilter
)

settings = get_settings()
logger = logging.getLogger(__name__)


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

    def _find_support_resistance(self, prices: pd.Series) -> tuple:
        prices_list = prices.tolist()
        supports = []
        resistances = []

        for i in range(2, len(prices_list) - 2):
            if prices_list[i] < min(prices_list[i-1], prices_list[i-2], prices_list[i+1], prices_list[i+2]):
                supports.append(prices_list[i])
            if prices_list[i] > max(prices_list[i-1], prices_list[i-2], prices_list[i+1], prices_list[i+2]):
                resistances.append(prices_list[i])

        supports = sorted(set(supports))[-3:] if supports else [prices.min()]
        resistances = sorted(set(resistances))[:3] if resistances else [prices.max()]

        return supports, resistances

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
        # Check cache
        cached = await self.repo.get_cached_analysis(symbol, AnalysisType.TECHNICAL)
        if cached:
            return TechnicalAnalysisResponse(
                symbol=symbol,
                current_price=cached.sma_20 or 0,
                indicators=[],
                overall_signal=SignalType(cached.overall_signal) if cached.overall_signal else SignalType.HOLD,
                signal_strength=cached.signal_strength or 0.5,
                technical_score=cached.technical_score or 0,
                support_levels=cached.support_levels or [],
                resistance_levels=cached.resistance_levels or [],
                trend="neutral",
                volatility="medium",
                generated_at=cached.created_at
            )

        df = await self._fetch_historical_data(symbol, period)
        if df is None or len(df) < 20:
            return None

        prices = df["close"]
        current_price = float(prices.iloc[-1])

        # Calculate indicators
        rsi = self._calculate_rsi(prices)
        macd, macd_signal = self._calculate_macd(prices)
        bb_upper, bb_lower, bb_middle = self._calculate_bollinger(prices)
        sma_20 = float(prices.rolling(20).mean().iloc[-1])
        sma_50 = float(prices.rolling(50).mean().iloc[-1]) if len(prices) >= 50 else sma_20
        supports, resistances = self._find_support_resistance(prices)

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

        # Cache result
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

        return TechnicalAnalysisResponse(
            symbol=symbol.upper(),
            current_price=current_price,
            indicators=indicators,
            overall_signal=signal,
            signal_strength=strength,
            technical_score=score,
            support_levels=[round(s, 2) for s in supports],
            resistance_levels=[round(r, 2) for r in resistances],
            trend=trend,
            volatility=volatility,
            generated_at=datetime.now()
        )

    async def get_fundamental_analysis(self, symbol: str) -> Optional[FundamentalAnalysisResponse]:
        # Fetch fundamental data from stock-data-service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}/api/v2/companies/{symbol}/financials",
                    timeout=30.0
                )
                if response.status_code != 200:
                    return None

                data = response.json()

                valuation = [
                    FundamentalMetric(name="P/E Ratio", value=data.get("pe_ratio"), rating=self._rate_pe(data.get("pe_ratio"))),
                    FundamentalMetric(name="P/B Ratio", value=data.get("pb_ratio")),
                    FundamentalMetric(name="EV/EBITDA", value=data.get("ev_ebitda")),
                ]

                profitability = [
                    FundamentalMetric(name="ROE", value=data.get("roe"), rating=self._rate_roe(data.get("roe"))),
                    FundamentalMetric(name="ROA", value=data.get("roa")),
                    FundamentalMetric(name="Profit Margin", value=data.get("profit_margin")),
                ]

                growth = [
                    FundamentalMetric(name="Revenue Growth", value=data.get("revenue_growth")),
                    FundamentalMetric(name="Earnings Growth", value=data.get("earnings_growth")),
                ]

                financial_health = [
                    FundamentalMetric(name="Current Ratio", value=data.get("current_ratio")),
                    FundamentalMetric(name="Debt to Equity", value=data.get("debt_to_equity")),
                ]

                score = self._calculate_fundamental_score(data)
                rating = "undervalued" if score > 70 else ("overvalued" if score < 40 else "fair")

                return FundamentalAnalysisResponse(
                    symbol=symbol.upper(),
                    company_name=data.get("company_name"),
                    valuation=valuation,
                    profitability=profitability,
                    growth=growth,
                    financial_health=financial_health,
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
