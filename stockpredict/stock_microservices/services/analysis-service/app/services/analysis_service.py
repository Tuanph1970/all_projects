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
    CompanyInfo, ValuationSummary, ValuationFactor, FinancialRatios,
    GrowthMetrics, IncomeStatement, BalanceSheet, CashFlow
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
            cached_price = cached.sma_20 or 0
            return TechnicalAnalysisResponse(
                symbol=symbol,
                current_price=CurrentPriceData(
                    price=cached_price,
                    open=None,
                    high=None,
                    low=None,
                    volume=None,
                    change=None,
                    change_percent=None
                ),
                indicators=[],
                moving_averages=MovingAverages(
                    SMA_20=cached.sma_20,
                    SMA_50=cached.sma_50,
                    SMA_200=None,
                    EMA_12=None,
                    EMA_26=None
                ),
                trading_analysis=TradingAnalysis(
                    recommendation=cached.overall_signal.upper() if cached.overall_signal else "HOLD",
                    score=cached.technical_score or 0,
                    confidence=cached.signal_strength or 0.5,
                    reasons=[]
                ),
                chart_data=None,
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
        sma_200 = float(prices.rolling(200).mean().iloc[-1]) if len(prices) >= 200 else None
        ema_12 = float(prices.ewm(span=12).mean().iloc[-1])
        ema_26 = float(prices.ewm(span=26).mean().iloc[-1])

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
                SMA_20=round(sma_20, 2),
                SMA_50=round(sma_50, 2),
                SMA_200=round(sma_200, 2) if sma_200 else None,
                EMA_12=round(ema_12, 2),
                EMA_26=round(ema_26, 2)
            ),
            trading_analysis=TradingAnalysis(
                recommendation=signal.value.upper().replace("_", " "),
                score=float(score),
                confidence=round(strength, 2),
                reasons=reasons
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
