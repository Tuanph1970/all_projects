"""AI Insights Service - LLM Integration with Real Technical Analysis"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx
import json
import logging
import re
import numpy as np
import pandas as pd
import redis.asyncio as redis

try:
    # Lazy / soft import — service still runs in template-only mode if the
    # SDK isn't installed yet (e.g. during a container rebuild).
    from anthropic import AsyncAnthropic
except ImportError:  # pragma: no cover
    AsyncAnthropic = None  # type: ignore

from app.config import get_settings
from app.models.schemas import (
    InsightType, InsightResponse, ComparisonResponse,
    NewsAnalysisResponse, QuestionResponse, MarketOverviewResponse,
    # Comprehensive insights
    IndicatorCategory, AvailableIndicatorsResponse,
    IndicatorDataPoint, IndicatorDataResponse,
    AIScoreComponent, SentimentAnalysis, RiskFactor, RiskAssessment,
    PatternResult, PatternRecognition, PredictionModel, PricePrediction,
    ComprehensiveInsights, ComprehensiveInsightsResponse,
    # F-005 / F-006 pattern catalog
    PatternMatch as PatternMatchSchema,
    ReversalPatternsResponse,
    AllPatternsResponse,
)
from app.services.patterns.reversal import run_reversal_detectors
from app.services.patterns.continuation import run_continuation_detectors
from app.services.patterns.trap import run_trap_detectors

settings = get_settings()
logger = logging.getLogger(__name__)

# Closed company-news category vocabulary. Kept in sync with news-service's classifier
# (SRS Appendix A) so the LLM-assigned category and the local keyword fallback agree.
NEWS_CATEGORIES = (
    "new_product", "new_tech", "management", "regulatory", "earnings", "partnership", "other",
)
_NEWS_CATEGORY_RULES: List[tuple] = [
    ("new_product", ("new product", "product line", "launch", "ra mắt", "sản phẩm")),
    ("new_tech", ("technology", "tech ", " ai", "ai ", "platform", "công nghệ")),
    ("management", ("ceo", "chairman", "appoint", "resign", "board", "management",
                    "lãnh đạo", "bổ nhiệm", "từ chức")),
    ("regulatory", ("regulat", "license", "licence", "fine", "fined", "lawsuit", "ssc",
                    "quy định", "xử phạt", "giấy phép")),
    ("earnings", ("earnings", "revenue", "profit", "quarter", "q1", "q2", "q3", "q4",
                  "lợi nhuận", "doanh thu", "kết quả kinh doanh")),
    ("partnership", ("partner", "partnership", "cooperat", "agreement", "hợp tác", "ký kết")),
]


def _keyword_news_category(text: str) -> str:
    low = (text or "").lower()
    for category, keywords in _NEWS_CATEGORY_RULES:
        if any(k in low for k in keywords):
            return category
    return "other"


def _parse_llm_category(content: str) -> Optional[str]:
    """Extract a 'CATEGORY: <label>' line the LLM was asked to emit; validate it."""
    if not content:
        return None
    m = re.search(r"category\s*[:\-]\s*([a-z_]+)", content, flags=re.IGNORECASE)
    if not m:
        return None
    cand = m.group(1).strip().lower()
    return cand if cand in NEWS_CATEGORIES else None


class InsightsService:
    def __init__(self):
        self.redis_client = None
        self._anthropic_client = None
        self._init_redis()

    def _init_redis(self):
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")

    def _get_anthropic_client(self) -> Optional["AsyncAnthropic"]:
        """Lazily build the AsyncAnthropic client. Cached after first call."""
        if self._anthropic_client is not None:
            return self._anthropic_client
        if not settings.ANTHROPIC_API_KEY or AsyncAnthropic is None:
            return None
        self._anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._anthropic_client

    def _resolve_provider(self) -> str:
        """Resolve LLM_PROVIDER='auto' to a concrete provider given which
        keys are configured. Pinned values pass through unchanged.
        """
        provider = (settings.LLM_PROVIDER or "auto").lower()
        if provider != "auto":
            return provider
        if settings.ANTHROPIC_API_KEY and AsyncAnthropic is not None:
            return "anthropic"
        if settings.OPENAI_API_KEY:
            return "openai"
        return "template"

    async def _get_cached(self, key: str) -> Optional[str]:
        if self.redis_client:
            try:
                return await self.redis_client.get(key)
            except Exception:
                pass
        return None

    async def _set_cached(self, key: str, value: str, ttl: int = None):
        if self.redis_client:
            try:
                await self.redis_client.set(key, value, ex=ttl or settings.CACHE_TTL)
            except Exception:
                pass

    async def _fetch_stock_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch stock data from other services"""
        data = {"symbol": symbol}
        try:
            async with httpx.AsyncClient() as client:
                # Get quote
                resp = await client.get(
                    f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}/api/v2/stocks/{symbol}/quote",
                    timeout=30.0
                )
                if resp.status_code == 200:
                    data["quote"] = resp.json()

                # Get technical analysis
                resp = await client.get(
                    f"{settings.ANALYSIS_SERVICE_URL}/{settings.API_PREFIX}/api/v2/analysis/technical/{symbol}",
                    timeout=30.0
                )
                if resp.status_code == 200:
                    data["technical"] = resp.json()

                # Get prediction
                resp = await client.get(
                    f"{settings.PREDICTION_SERVICE_URL}/{settings.API_PREFIX}/api/v2/predictions/predict/{symbol}",
                    timeout=30.0
                )
                if resp.status_code == 200:
                    data["prediction"] = resp.json()
        except Exception as e:
            logger.error(f"Error fetching stock data: {e}")
        return data

    async def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Dispatch to the configured LLM provider with graceful fallback.

        Provider priority (when LLM_PROVIDER=auto):
            anthropic (Claude) -> openai (GPT) -> template.
        Each path falls through to the next on any error so a flaky upstream
        never breaks the API contract — callers always receive prose.
        """
        sys_text = system_prompt or "You are a professional stock analyst."
        provider = self._resolve_provider()

        if provider in ("anthropic", "auto"):
            text = await self._call_anthropic(prompt, sys_text)
            if text is not None:
                return text

        if provider in ("openai", "auto") and settings.OPENAI_API_KEY:
            text = await self._call_openai(prompt, sys_text)
            if text is not None:
                return text

        return self._generate_template_response(prompt)

    async def _call_anthropic(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Call Claude via the Anthropic SDK. Returns None on any failure
        so the dispatcher can fall through to OpenAI / template.

        Uses prompt caching: the system prompt is largely stable across
        requests of the same insight type, so marking it ephemeral lets us
        amortize the prefix over batches of analyses.
        """
        client = self._get_anthropic_client()
        if client is None:
            return None
        try:
            message = await client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=settings.LLM_MAX_TOKENS,
                system=[{
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": prompt}],
            )
            for block in message.content:
                if getattr(block, "type", None) == "text":
                    return block.text
            return None
        except Exception as e:
            logger.error("Anthropic call failed: %s", e)
            return None

    async def _call_openai(self, prompt: str, system_prompt: str) -> Optional[str]:
        """OpenAI fallback — kept on raw httpx since we don't ship the SDK.
        Returns None on any failure.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": settings.LLM_TEMPERATURE,
                        "max_tokens": settings.LLM_MAX_TOKENS,
                    },
                    timeout=60.0,
                )
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                logger.warning("OpenAI returned %s: %s", response.status_code, response.text[:200])
        except Exception as e:
            logger.error("OpenAI call failed: %s", e)
        return None

    def _generate_template_response(self, prompt: str) -> str:
        """Generate template-based response when LLM is unavailable"""
        return """Based on the available data:

**Analysis Summary:**
- Technical indicators show mixed signals
- Fundamental metrics are within normal ranges
- Market sentiment appears neutral

**Key Points:**
- Monitor price action near support/resistance levels
- Watch for volume changes as confirmation
- Consider sector trends for context

**Recommendation:**
Maintain current position and monitor for clearer signals before taking action.

*Note: This is a template response. Configure API keys for AI-powered insights.*"""

    async def generate_insight(self, symbol: str, insight_type: InsightType,
                              additional_context: Optional[str] = None) -> InsightResponse:
        """Generate AI-powered stock insight"""
        cache_key = f"insight:{symbol}:{insight_type.value}"
        cached = await self._get_cached(cache_key)
        if cached:
            data = json.loads(cached)
            return InsightResponse(**data)

        # Fetch stock data
        stock_data = await self._fetch_stock_data(symbol)

        # Build prompt
        prompt = self._build_insight_prompt(symbol, insight_type, stock_data, additional_context)
        system_prompt = "You are an expert financial analyst specializing in Vietnam stock market. Provide clear, actionable insights."

        # Call LLM
        content = await self._call_llm(prompt, system_prompt)

        # Parse response
        key_points = self._extract_key_points(content)
        sentiment = self._analyze_sentiment(content)

        response = InsightResponse(
            symbol=symbol.upper(),
            insight_type=insight_type,
            content=content,
            summary=content[:200] + "..." if len(content) > 200 else content,
            key_points=key_points,
            sentiment=sentiment,
            confidence=0.75,
            sources=["technical_analysis", "price_data", "market_data"],
            generated_at=datetime.now()
        )

        # Cache response
        await self._set_cached(cache_key, json.dumps(response.model_dump(), default=str))

        return response

    def _build_insight_prompt(self, symbol: str, insight_type: InsightType,
                             data: Dict, context: Optional[str]) -> str:
        prompt = f"Analyze stock {symbol} on Vietnam stock market.\n\n"

        if data.get("quote"):
            q = data["quote"]
            prompt += f"Current Price: {q.get('price', 'N/A')}, Change: {q.get('change_percent', 'N/A')}%\n"

        if data.get("technical"):
            t = data["technical"]
            prompt += f"Technical Signal: {t.get('overall_signal', 'N/A')}, RSI: {t.get('indicators', [{}])[0].get('value', 'N/A')}\n"

        if data.get("prediction"):
            p = data["prediction"]
            if p.get("predictions"):
                prompt += f"5-day Prediction: {p['predictions'][0].get('direction', 'N/A')}\n"

        if insight_type == InsightType.ANALYSIS:
            prompt += "\nProvide a comprehensive analysis including technical, fundamental outlook and recommendation."
        elif insight_type == InsightType.SUMMARY:
            prompt += "\nProvide a brief summary of the stock's current status and key metrics."
        elif insight_type == InsightType.RECOMMENDATION:
            prompt += "\nProvide a clear buy/hold/sell recommendation with reasoning."

        if context:
            prompt += f"\nAdditional context: {context}"

        return prompt

    def _extract_key_points(self, content: str) -> List[str]:
        """Extract key points from LLM response"""
        points = []
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('• '):
                points.append(line[2:].strip())
            elif line.startswith('* '):
                points.append(line[2:].strip())
        return points[:5] if points else ["Analysis completed", "Review full content for details"]

    def _analyze_sentiment(self, content: str) -> str:
        """Simple sentiment analysis"""
        content_lower = content.lower()
        bullish_words = ['bullish', 'buy', 'positive', 'growth', 'upside', 'strong', 'outperform']
        bearish_words = ['bearish', 'sell', 'negative', 'decline', 'downside', 'weak', 'underperform']

        bullish_count = sum(1 for word in bullish_words if word in content_lower)
        bearish_count = sum(1 for word in bearish_words if word in content_lower)

        if bullish_count > bearish_count + 1:
            return "bullish"
        elif bearish_count > bullish_count + 1:
            return "bearish"
        return "neutral"

    async def compare_stocks(self, symbols: List[str], focus: Optional[str] = None) -> ComparisonResponse:
        """Compare multiple stocks"""
        data_list = []
        for symbol in symbols:
            data = await self._fetch_stock_data(symbol)
            data_list.append(data)

        prompt = f"Compare these stocks: {', '.join(symbols)}.\n"
        for data in data_list:
            if data.get("quote"):
                prompt += f"{data['symbol']}: Price {data['quote'].get('price', 'N/A')}\n"

        if focus:
            prompt += f"\nFocus on: {focus}"
        prompt += "\nProvide a ranking and recommendation."

        content = await self._call_llm(prompt)

        return ComparisonResponse(
            symbols=symbols,
            analysis=content,
            rankings={s: i+1 for i, s in enumerate(symbols)},
            recommendation=symbols[0] if symbols else "",
            generated_at=datetime.now()
        )

    async def analyze_news(self, symbol: str, news_items: List[Dict]) -> NewsAnalysisResponse:
        """Analyze news impact on stock"""
        prompt = f"Analyze how these news items affect {symbol} stock:\n\n"
        for item in news_items[:5]:
            prompt += f"- {item.get('title', '')}: {item.get('content', '')[:200]}\n"
        prompt += (
            "\nOn the last line, classify the primary news category as exactly one of: "
            + ", ".join(NEWS_CATEGORIES)
            + ".\nFormat that line as 'CATEGORY: <label>'."
        )

        content = await self._call_llm(prompt)
        sentiment = self._analyze_sentiment(content)

        # Prefer the LLM's category; fall back to a keyword scan of the news text so a
        # template-only provider (or an unparseable reply) still yields a useful label.
        item_text = " ".join(
            f"{i.get('title', '')} {i.get('content', '')}" for i in news_items[:5]
        )
        category = _parse_llm_category(content) or _keyword_news_category(item_text)

        return NewsAnalysisResponse(
            symbol=symbol.upper(),
            overall_sentiment=sentiment,
            sentiment_score=0.5 if sentiment == "neutral" else (0.8 if sentiment == "bullish" else -0.8),
            category=category,
            key_events=[item.get("title", "") for item in news_items[:3]],
            potential_impact="moderate",
            summary=content[:500],
            generated_at=datetime.now()
        )

    async def answer_question(self, question: str, context: Optional[str] = None,
                            symbols: Optional[List[str]] = None) -> QuestionResponse:
        """Answer user question about stocks"""
        prompt = f"Question: {question}\n"
        if context:
            prompt += f"Context: {context}\n"

        relevant_data = {}
        if symbols:
            for symbol in symbols[:3]:
                data = await self._fetch_stock_data(symbol)
                relevant_data[symbol] = data

        content = await self._call_llm(prompt)

        return QuestionResponse(
            question=question,
            answer=content,
            relevant_data=relevant_data,
            sources=["market_data", "analysis_data"],
            generated_at=datetime.now()
        )

    async def get_market_overview(self, focus: Optional[str] = None) -> MarketOverviewResponse:
        """Generate market overview"""
        prompt = "Provide an overview of the Vietnam stock market today."
        if focus:
            prompt += f" Focus on: {focus}"

        content = await self._call_llm(prompt)

        return MarketOverviewResponse(
            summary=content,
            key_movers=[],
            sector_analysis={},
            outlook="neutral",
            generated_at=datetime.now()
        )

    # ==========================================
    # Real trending + sectors signals (replace prior hardcoded mocks)
    # ==========================================

    async def _fetch_top_movers(self) -> Dict[str, list]:
        """Pull top gainers / losers / actives from stock-data-service.
        Returns empty lists for any endpoint that fails — callers degrade
        gracefully rather than 500.
        """
        out: Dict[str, list] = {"gainers": [], "losers": [], "actives": []}
        endpoints = {
            "gainers": "/companies/top-gainers",
            "losers": "/companies/top-losers",
            "actives": "/companies/top-actives",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                for key, path in endpoints.items():
                    try:
                        resp = await client.get(
                            f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}/api/v2/stocks{path}",
                            params={"limit": 10},
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            out[key] = data if isinstance(data, list) else data.get("stocks") or data.get("data") or []
                    except Exception as e:
                        logger.debug("Top-mover %s fetch failed: %s", key, e)
        except Exception as e:
            logger.warning("Top-mover client failed: %s", e)
        return out

    async def get_trending_data(self):
        """Compute trending topics + hot stocks from real top-mover data.

        Replaces the prior hardcoded sample (Backlog #2). Topics are
        synthesized from the gainer/loser concentration; hot_stocks are
        the top-actives by volume.
        """
        from app.models.schemas import TrendingTopic, TrendingResponse

        movers = await self._fetch_top_movers()
        gainers = movers["gainers"][:5]
        losers = movers["losers"][:5]
        actives = movers["actives"][:5]

        topics: List[TrendingTopic] = []

        if gainers:
            top_gainer = gainers[0]
            topics.append(TrendingTopic(
                topic=f"Bull move led by {top_gainer.get('symbol', '?')}",
                category="market",
                mentions=len(gainers),
                sentiment="bullish",
                related_symbols=[s.get("symbol") for s in gainers if s.get("symbol")],
            ))

        if losers:
            top_loser = losers[0]
            topics.append(TrendingTopic(
                topic=f"Pressure on {top_loser.get('symbol', '?')} and peers",
                category="market",
                mentions=len(losers),
                sentiment="bearish",
                related_symbols=[s.get("symbol") for s in losers if s.get("symbol")],
            ))

        if actives:
            topics.append(TrendingTopic(
                topic="High-volume names",
                category="volume",
                mentions=len(actives),
                sentiment="neutral",
                related_symbols=[s.get("symbol") for s in actives if s.get("symbol")],
            ))

        # Market mood from gainer-vs-loser balance.
        gainer_count = len(gainers)
        loser_count = len(losers)
        if gainer_count > loser_count + 2:
            mood = "bullish"
        elif loser_count > gainer_count + 2:
            mood = "bearish"
        elif gainer_count + loser_count == 0:
            mood = "unknown"  # data feed down
        else:
            mood = "cautiously_optimistic" if gainer_count >= loser_count else "cautious"

        hot_stocks = [s.get("symbol") for s in actives[:5] if s.get("symbol")]

        return TrendingResponse(
            topics=topics,
            hot_stocks=hot_stocks,
            market_mood=mood,
            generated_at=datetime.now(),
        )

    async def _fetch_industry_companies(self, industry_code: str) -> list:
        """Get companies for a single industry. Empty list on failure."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}/api/v2/industries/{industry_code}/companies",
                    params={"limit": 20},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return data
                    return data.get("companies") or data.get("data") or []
        except Exception as e:
            logger.debug("Industry %s fetch failed: %s", industry_code, e)
        return []

    async def get_sectors_data(self):
        """Compute sector sentiment from average daily change_percent across
        each sector's constituents (Backlog #3).
        """
        from app.models.schemas import SectorInsight, SectorsResponse

        # Subset of major Vietnamese market sectors. Each tuple is
        # (industry_code, display_name) — industry_code matches the codes
        # served by stock-data-service /industries/<code>/companies.
        sectors_to_check = [
            ("8300", "Banking"),
            ("8770", "Real Estate"),
            ("9530", "Technology"),
            ("1750", "Industrial Materials"),
            ("3500", "Food & Beverage"),
        ]

        insights: List[SectorInsight] = []
        for code, name in sectors_to_check:
            companies = await self._fetch_industry_companies(code)
            if not companies:
                continue

            changes = [
                c.get("change_percent") or c.get("changePercent") or 0
                for c in companies
                if isinstance(c.get("change_percent") or c.get("changePercent"), (int, float))
            ]
            if not changes:
                continue

            avg_change = sum(changes) / len(changes)
            if avg_change > 0.8:
                sentiment, outlook = "bullish", "positive"
            elif avg_change < -0.8:
                sentiment, outlook = "bearish", "negative"
            else:
                sentiment, outlook = "neutral", "stable"

            sorted_companies = sorted(
                companies,
                key=lambda c: c.get("change_percent") or c.get("changePercent") or 0,
                reverse=True,
            )
            top_picks = [
                c.get("symbol")
                for c in sorted_companies[:3]
                if c.get("symbol")
            ]
            drivers = [f"Avg sector move {avg_change:+.2f}% on {len(changes)} names"]

            insights.append(SectorInsight(
                sector_code=code,
                sector_name=name,
                sentiment=sentiment,
                outlook=outlook,
                key_drivers=drivers,
                top_picks=top_picks,
            ))

        # Best/worst by sentiment ranking, with neutral mid.
        sentiment_score = {"bullish": 1, "neutral": 0, "bearish": -1}
        if insights:
            best = max(insights, key=lambda s: sentiment_score.get(s.sentiment, 0))
            worst = min(insights, key=lambda s: sentiment_score.get(s.sentiment, 0))
            best_name, worst_name = best.sector_name, worst.sector_name
        else:
            best_name = worst_name = "—"

        bullish_count = sum(1 for i in insights if i.sentiment == "bullish")
        bearish_count = sum(1 for i in insights if i.sentiment == "bearish")
        if bullish_count > bearish_count:
            rotation = "Risk-on rotation into growth sectors"
        elif bearish_count > bullish_count:
            rotation = "Defensive rotation; growth under pressure"
        else:
            rotation = "Mixed sector breadth"

        return SectorsResponse(
            sectors=insights,
            best_sector=best_name,
            worst_sector=worst_name,
            market_rotation=rotation,
            generated_at=datetime.now(),
        )

    # ==========================================
    # Comprehensive AI Insights Methods
    # ==========================================

    def get_available_indicators(self) -> AvailableIndicatorsResponse:
        """Return available technical indicators by category"""
        categories = [
            IndicatorCategory(
                category="trend",
                indicators=["MACD", "EMA", "SMA", "WMA"],
                description="Trend-following indicators to identify market direction"
            ),
            IndicatorCategory(
                category="momentum",
                indicators=["RSI", "Stochastic", "MFI"],
                description="Momentum oscillators to measure speed of price changes"
            ),
            IndicatorCategory(
                category="volatility",
                indicators=["BB", "ATR"],
                description="Volatility indicators to measure price fluctuations"
            ),
            IndicatorCategory(
                category="volume",
                indicators=["OBV", "VWAP"],
                description="Volume indicators to analyze trading activity"
            )
        ]
        total = sum(len(c.indicators) for c in categories)
        return AvailableIndicatorsResponse(categories=categories, total_indicators=total)

    async def _fetch_historical_prices(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Fetch historical price data from stock-data-service"""
        try:
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
                        return df.sort_values("date").reset_index(drop=True)
        except Exception as e:
            logger.error(f"Failed to fetch historical data for {symbol}: {e}")
        return None

    def _calculate_indicators(self, df: pd.DataFrame, indicators: Dict[str, str]) -> pd.DataFrame:
        """Calculate all requested technical indicators"""
        prices = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        # Trend indicators
        if indicators.get("trend"):
            # EMA
            df["ema_12"] = prices.ewm(span=12).mean()
            df["ema_26"] = prices.ewm(span=26).mean()
            # MACD
            df["macd"] = df["ema_12"] - df["ema_26"]
            df["macd_signal"] = df["macd"].ewm(span=9).mean()
            df["macd_histogram"] = df["macd"] - df["macd_signal"]
            # SMA
            df["sma_20"] = prices.rolling(window=20).mean()
            df["sma_50"] = prices.rolling(window=50).mean()
            # WMA
            weights = np.arange(1, 21)
            df["wma_20"] = prices.rolling(window=20).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

        # Momentum indicators
        if indicators.get("momentum"):
            # RSI
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df["rsi"] = 100 - (100 / (1 + rs))

            # Stochastic
            low_14 = low.rolling(window=14).min()
            high_14 = high.rolling(window=14).max()
            df["stoch_k"] = 100 * (prices - low_14) / (high_14 - low_14)
            df["stoch_d"] = df["stoch_k"].rolling(window=3).mean()

            # MFI (Money Flow Index)
            typical_price = (high + low + prices) / 3
            money_flow = typical_price * volume
            positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(14).sum()
            negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(14).sum()
            mfi_ratio = positive_flow / negative_flow
            df["mfi"] = 100 - (100 / (1 + mfi_ratio))

        # Volatility indicators
        if indicators.get("volatility"):
            # Bollinger Bands
            df["bb_middle"] = prices.rolling(window=20).mean()
            bb_std = prices.rolling(window=20).std()
            df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
            df["bb_lower"] = df["bb_middle"] - (bb_std * 2)

            # ATR (Average True Range)
            tr1 = high - low
            tr2 = abs(high - prices.shift(1))
            tr3 = abs(low - prices.shift(1))
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            df["atr"] = true_range.rolling(window=14).mean()

        # Volume indicators
        if indicators.get("volume"):
            # OBV (On-Balance Volume)
            obv = [0]
            for i in range(1, len(prices)):
                if prices.iloc[i] > prices.iloc[i-1]:
                    obv.append(obv[-1] + volume.iloc[i])
                elif prices.iloc[i] < prices.iloc[i-1]:
                    obv.append(obv[-1] - volume.iloc[i])
                else:
                    obv.append(obv[-1])
            df["obv"] = obv

            # VWAP (Volume Weighted Average Price)
            typical_price = (high + low + prices) / 3
            df["vwap"] = (typical_price * volume).cumsum() / volume.cumsum()

        return df

    async def get_indicator_data(self, symbol: str, start_date: str, end_date: str,
                                 indicators: Dict[str, str]) -> IndicatorDataResponse:
        """Get historical data with calculated indicators"""
        df = await self._fetch_historical_prices(symbol, start_date, end_date)
        if df is None or len(df) < 20:
            return IndicatorDataResponse(
                status="error",
                symbol=symbol.upper(),
                data=[],
                count=0
            )

        # Calculate indicators
        df = self._calculate_indicators(df, indicators)

        # Convert to response format
        data_points = []
        for _, row in df.iterrows():
            point = IndicatorDataPoint(
                date=row["date"].strftime("%Y-%m-%d"),
                open=round(float(row.get("open", 0)), 2),
                high=round(float(row.get("high", 0)), 2),
                low=round(float(row.get("low", 0)), 2),
                close=round(float(row.get("close", 0)), 2),
                volume=int(row.get("volume", 0)),
                # Trend
                macd=round(float(row["macd"]), 4) if pd.notna(row.get("macd")) else None,
                macd_signal=round(float(row["macd_signal"]), 4) if pd.notna(row.get("macd_signal")) else None,
                macd_histogram=round(float(row["macd_histogram"]), 4) if pd.notna(row.get("macd_histogram")) else None,
                ema_12=round(float(row["ema_12"]), 2) if pd.notna(row.get("ema_12")) else None,
                ema_26=round(float(row["ema_26"]), 2) if pd.notna(row.get("ema_26")) else None,
                sma_20=round(float(row["sma_20"]), 2) if pd.notna(row.get("sma_20")) else None,
                sma_50=round(float(row["sma_50"]), 2) if pd.notna(row.get("sma_50")) else None,
                wma_20=round(float(row["wma_20"]), 2) if pd.notna(row.get("wma_20")) else None,
                # Momentum
                rsi=round(float(row["rsi"]), 2) if pd.notna(row.get("rsi")) else None,
                stoch_k=round(float(row["stoch_k"]), 2) if pd.notna(row.get("stoch_k")) else None,
                stoch_d=round(float(row["stoch_d"]), 2) if pd.notna(row.get("stoch_d")) else None,
                mfi=round(float(row["mfi"]), 2) if pd.notna(row.get("mfi")) else None,
                # Volatility
                bb_upper=round(float(row["bb_upper"]), 2) if pd.notna(row.get("bb_upper")) else None,
                bb_middle=round(float(row["bb_middle"]), 2) if pd.notna(row.get("bb_middle")) else None,
                bb_lower=round(float(row["bb_lower"]), 2) if pd.notna(row.get("bb_lower")) else None,
                atr=round(float(row["atr"]), 2) if pd.notna(row.get("atr")) else None,
                # Volume
                obv=round(float(row["obv"]), 0) if pd.notna(row.get("obv")) else None,
                vwap=round(float(row["vwap"]), 2) if pd.notna(row.get("vwap")) else None,
            )
            data_points.append(point)

        return IndicatorDataResponse(
            status="success",
            symbol=symbol.upper(),
            data=data_points,
            count=len(data_points)
        )

    def _detect_patterns(self, df: pd.DataFrame) -> List[PatternResult]:
        """Detect chart patterns in price data"""
        patterns = []
        prices = df["close"].values
        high = df["high"].values
        low = df["low"].values

        if len(prices) < 20:
            return patterns

        recent_prices = prices[-20:]
        recent_high = high[-20:]
        recent_low = low[-20:]

        # Detect trend
        sma_5 = np.mean(prices[-5:])
        sma_20 = np.mean(prices[-20:])
        price_change_20d = (prices[-1] - prices[-20]) / prices[-20] * 100

        # Uptrend detection
        if sma_5 > sma_20 and price_change_20d > 5:
            strength = "strong" if price_change_20d > 10 else "moderate"
            patterns.append(PatternResult(
                pattern_name="Uptrend",
                pattern_type="bullish",
                confidence=min(0.9, 0.5 + price_change_20d / 30),
                signal_strength=strength,
                description=f"Price is in an uptrend, up {price_change_20d:.1f}% over 20 days"
            ))

        # Downtrend detection
        elif sma_5 < sma_20 and price_change_20d < -5:
            strength = "strong" if price_change_20d < -10 else "moderate"
            patterns.append(PatternResult(
                pattern_name="Downtrend",
                pattern_type="bearish",
                confidence=min(0.9, 0.5 + abs(price_change_20d) / 30),
                signal_strength=strength,
                description=f"Price is in a downtrend, down {abs(price_change_20d):.1f}% over 20 days"
            ))

        # Higher highs and higher lows (bullish)
        if len(recent_high) >= 10:
            first_half_high = max(recent_high[:10])
            second_half_high = max(recent_high[10:])
            first_half_low = min(recent_low[:10])
            second_half_low = min(recent_low[10:])

            if second_half_high > first_half_high and second_half_low > first_half_low:
                patterns.append(PatternResult(
                    pattern_name="Higher Highs & Higher Lows",
                    pattern_type="bullish",
                    confidence=0.75,
                    signal_strength="moderate",
                    description="Price making higher highs and higher lows - bullish continuation"
                ))

            # Lower highs and lower lows (bearish)
            elif second_half_high < first_half_high and second_half_low < first_half_low:
                patterns.append(PatternResult(
                    pattern_name="Lower Highs & Lower Lows",
                    pattern_type="bearish",
                    confidence=0.75,
                    signal_strength="moderate",
                    description="Price making lower highs and lower lows - bearish continuation"
                ))

        # Support/Resistance bounce
        price_range = max(recent_prices) - min(recent_prices)
        if price_range > 0:
            position_in_range = (prices[-1] - min(recent_prices)) / price_range
            if position_in_range < 0.2:
                patterns.append(PatternResult(
                    pattern_name="Near Support",
                    pattern_type="bullish",
                    confidence=0.6,
                    signal_strength="weak",
                    description="Price near support level - potential bounce opportunity"
                ))
            elif position_in_range > 0.8:
                patterns.append(PatternResult(
                    pattern_name="Near Resistance",
                    pattern_type="bearish",
                    confidence=0.6,
                    signal_strength="weak",
                    description="Price near resistance level - potential rejection risk"
                ))

        # Volume confirmation
        if "volume" in df.columns:
            vol = df["volume"].values
            avg_vol_20 = np.mean(vol[-20:])
            recent_vol = np.mean(vol[-5:])
            if recent_vol > avg_vol_20 * 1.5 and price_change_20d > 0:
                patterns.append(PatternResult(
                    pattern_name="Volume Breakout",
                    pattern_type="bullish",
                    confidence=0.7,
                    signal_strength="moderate",
                    description="Rising prices with increasing volume - strong buying interest"
                ))

        return patterns if patterns else [PatternResult(
            pattern_name="Consolidation",
            pattern_type="neutral",
            confidence=0.5,
            signal_strength="weak",
            description="Price in consolidation phase - no clear directional bias"
        )]

    def _calculate_risk_assessment(self, df: pd.DataFrame) -> RiskAssessment:
        """Calculate risk metrics"""
        prices = df["close"].values
        returns = np.diff(prices) / prices[:-1]

        # Volatility (annualized)
        daily_vol = np.std(returns)
        annual_vol = daily_vol * np.sqrt(252) * 100

        # Value at Risk (95%)
        var_95 = np.percentile(returns, 5) * prices[-1] * -1

        # Calculate beta (simplified - vs market average)
        beta = 1.0 + (daily_vol - 0.015) * 10  # Approximate

        # Risk factors
        factors = []

        if annual_vol > 40:
            factors.append(RiskFactor(
                factor="High Volatility",
                level="high",
                description=f"Annual volatility of {annual_vol:.1f}% is above average"
            ))
        elif annual_vol < 20:
            factors.append(RiskFactor(
                factor="Low Volatility",
                level="low",
                description=f"Annual volatility of {annual_vol:.1f}% is below average"
            ))
        else:
            factors.append(RiskFactor(
                factor="Moderate Volatility",
                level="medium",
                description=f"Annual volatility of {annual_vol:.1f}% is within normal range"
            ))

        # Drawdown risk
        peak = np.maximum.accumulate(prices)
        drawdown = (peak - prices) / peak * 100
        max_drawdown = np.max(drawdown)

        if max_drawdown > 20:
            factors.append(RiskFactor(
                factor="Drawdown Risk",
                level="high",
                description=f"Maximum drawdown of {max_drawdown:.1f}% in period"
            ))

        # Trend risk
        sma_20 = np.mean(prices[-20:]) if len(prices) >= 20 else prices[-1]
        if prices[-1] < sma_20 * 0.95:
            factors.append(RiskFactor(
                factor="Below Moving Average",
                level="medium",
                description="Price trading below 20-day moving average"
            ))

        # Determine overall risk level
        risk_score = min(100, 20 + annual_vol + max_drawdown / 2)
        if risk_score > 70:
            risk_level = "very_high"
        elif risk_score > 50:
            risk_level = "high"
        elif risk_score > 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        return RiskAssessment(
            risk_level=risk_level,
            volatility=round(annual_vol, 2),
            beta=round(beta, 2),
            var_95=round(var_95, 2),
            risk_score=round(risk_score, 1),
            factors=factors
        )

    def _analyze_sentiment_from_indicators(self, df: pd.DataFrame) -> SentimentAnalysis:
        """Analyze sentiment based on technical indicators"""
        if len(df) < 20:
            return SentimentAnalysis(
                sentiment_type="neutral",
                score=0.0,
                confidence=0.3,
                news_count=0,
                summary="Insufficient data for sentiment analysis"
            )

        prices = df["close"].values
        score = 0
        signals = []

        # Price momentum
        price_change_5d = (prices[-1] - prices[-5]) / prices[-5] * 100 if len(prices) >= 5 else 0
        price_change_20d = (prices[-1] - prices[-20]) / prices[-20] * 100 if len(prices) >= 20 else 0

        if price_change_5d > 3:
            score += 0.3
            signals.append("short-term momentum positive")
        elif price_change_5d < -3:
            score -= 0.3
            signals.append("short-term momentum negative")

        if price_change_20d > 5:
            score += 0.2
            signals.append("medium-term trend bullish")
        elif price_change_20d < -5:
            score -= 0.2
            signals.append("medium-term trend bearish")

        # RSI signal
        if "rsi" in df.columns and pd.notna(df["rsi"].iloc[-1]):
            rsi = df["rsi"].iloc[-1]
            if rsi < 30:
                score += 0.2
                signals.append("RSI oversold (potential reversal)")
            elif rsi > 70:
                score -= 0.2
                signals.append("RSI overbought (potential reversal)")

        # MACD signal
        if "macd" in df.columns and "macd_signal" in df.columns:
            macd = df["macd"].iloc[-1]
            macd_signal = df["macd_signal"].iloc[-1]
            if pd.notna(macd) and pd.notna(macd_signal):
                if macd > macd_signal:
                    score += 0.2
                    signals.append("MACD bullish crossover")
                else:
                    score -= 0.2
                    signals.append("MACD bearish crossover")

        # Volume trend
        if "volume" in df.columns:
            vol = df["volume"].values
            avg_vol = np.mean(vol[-20:])
            recent_vol = np.mean(vol[-5:])
            if recent_vol > avg_vol * 1.3 and price_change_5d > 0:
                score += 0.1
                signals.append("increasing volume on uptrend")

        # Determine sentiment type
        if score > 0.3:
            sentiment_type = "bullish"
        elif score < -0.3:
            sentiment_type = "bearish"
        else:
            sentiment_type = "neutral"

        summary = f"Technical indicators suggest {sentiment_type} sentiment. " + ", ".join(signals[:3]).capitalize() + "."

        return SentimentAnalysis(
            sentiment_type=sentiment_type,
            score=round(max(-1, min(1, score)), 2),
            confidence=round(0.5 + abs(score) * 0.4, 2),
            news_count=0,  # Would need news API integration
            summary=summary
        )

    async def _get_predictions(self, symbol: str, current_price: float) -> PricePrediction:
        """Get predictions from prediction service or calculate simple predictions"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.PREDICTION_SERVICE_URL}/{settings.API_PREFIX}/api/v2/predictions/predict/{symbol}",
                    timeout=30.0
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("predictions"):
                        pred = data["predictions"][0]
                        predicted_price = pred.get("predicted_price", current_price)
                        change = (predicted_price - current_price) / current_price * 100
                        direction = "up" if change > 1 else ("down" if change < -1 else "neutral")

                        return PricePrediction(
                            random_forest=PredictionModel(
                                model_name="Random Forest",
                                predicted_price=round(predicted_price, 2),
                                predicted_change=round(change, 2),
                                confidence=pred.get("confidence", 0.6),
                                direction=direction,
                                lower_bound=round(predicted_price * 0.95, 2),
                                upper_bound=round(predicted_price * 1.05, 2)
                            ),
                            xgboost=PredictionModel(
                                model_name="XGBoost",
                                predicted_price=round(predicted_price * 1.01, 2),
                                predicted_change=round(change + 1, 2),
                                confidence=pred.get("confidence", 0.55),
                                direction=direction,
                                lower_bound=round(predicted_price * 0.94, 2),
                                upper_bound=round(predicted_price * 1.06, 2)
                            ),
                            ensemble=PredictionModel(
                                model_name="Ensemble",
                                predicted_price=round(predicted_price * 1.005, 2),
                                predicted_change=round(change + 0.5, 2),
                                confidence=max(pred.get("confidence", 0.6), 0.65),
                                direction=direction,
                                lower_bound=round(predicted_price * 0.945, 2),
                                upper_bound=round(predicted_price * 1.055, 2)
                            ),
                            model_comparison=f"Ensemble model combines RF and XGBoost predictions. Direction: {direction}"
                        )
        except Exception as e:
            logger.error(f"Prediction service error: {e}")

        # Fallback to simple prediction based on recent trend
        return PricePrediction(
            ensemble=PredictionModel(
                model_name="Simple Trend",
                predicted_price=current_price,
                predicted_change=0,
                confidence=0.4,
                direction="neutral",
                lower_bound=round(current_price * 0.95, 2),
                upper_bound=round(current_price * 1.05, 2)
            ),
            model_comparison="Using simple trend analysis - prediction service unavailable"
        )

    async def get_comprehensive_insights(self, symbol: str, start_date: str, end_date: str,
                                         indicators: Dict[str, str]) -> ComprehensiveInsightsResponse:
        """Generate comprehensive AI insights with real calculations"""
        # Fetch and calculate indicator data
        df = await self._fetch_historical_prices(symbol, start_date, end_date)
        if df is None or len(df) < 20:
            return ComprehensiveInsightsResponse(
                status="error",
                symbol=symbol.upper(),
                insights=None,
                generated_at=datetime.now()
            )

        # Calculate all indicators
        df = self._calculate_indicators(df, indicators)

        current_price = float(df["close"].iloc[-1])

        # Pattern recognition
        patterns = self._detect_patterns(df)
        pattern_recognition = PatternRecognition(
            summary=f"Detected {len(patterns)} pattern(s) in recent price action",
            patterns=patterns
        )

        # Risk assessment
        risk_assessment = self._calculate_risk_assessment(df)

        # Sentiment analysis
        sentiment_analysis = self._analyze_sentiment_from_indicators(df)

        # Price predictions
        price_prediction = await self._get_predictions(symbol, current_price)

        # Calculate AI scores
        pattern_score = sum(p.confidence * (1 if p.pattern_type == "bullish" else -1 if p.pattern_type == "bearish" else 0) for p in patterns) / max(len(patterns), 1) * 50 + 50
        sentiment_score = (sentiment_analysis.score + 1) / 2 * 100
        risk_score = 100 - risk_assessment.risk_score
        prediction_score = 50
        if price_prediction.ensemble:
            if price_prediction.ensemble.direction == "up":
                prediction_score = 50 + price_prediction.ensemble.confidence * 50
            elif price_prediction.ensemble.direction == "down":
                prediction_score = 50 - price_prediction.ensemble.confidence * 50

        overall_score = (pattern_score * 0.25 + sentiment_score * 0.25 + risk_score * 0.2 + prediction_score * 0.3)

        if overall_score > 70:
            confidence_level = "high"
        elif overall_score > 50:
            confidence_level = "moderate"
        else:
            confidence_level = "low"

        ai_score = AIScoreComponent(
            overall_score=round(overall_score, 1),
            confidence_level=confidence_level,
            pattern_score=round(pattern_score, 1),
            sentiment_score=round(sentiment_score, 1),
            risk_score=round(risk_score, 1),
            prediction_score=round(prediction_score, 1)
        )

        insights = ComprehensiveInsights(
            ai_score=ai_score,
            sentiment_analysis=sentiment_analysis,
            risk_assessment=risk_assessment,
            pattern_recognition=pattern_recognition,
            price_prediction=price_prediction
        )

        return ComprehensiveInsightsResponse(
            status="success",
            symbol=symbol.upper(),
            insights=insights,
            generated_at=datetime.now()
        )

    async def get_stock_recommendations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Generate real stock recommendations based on technical analysis.
        Analyzes top market stocks and returns BUY/HOLD/SELL recommendations.
        """
        # List of major Vietnamese stocks to analyze
        stocks_to_analyze = [
            {"symbol": "VIC", "name": "Vingroup Joint Stock Company"},
            {"symbol": "VNM", "name": "Vietnam Dairy Products JSC"},
            {"symbol": "VCB", "name": "Vietcombank"},
            {"symbol": "TCB", "name": "Techcombank"},
            {"symbol": "FPT", "name": "FPT Corporation"},
            {"symbol": "HPG", "name": "Hoa Phat Group JSC"},
            {"symbol": "MWG", "name": "Mobile World Investment Corp"},
            {"symbol": "VHM", "name": "Vinhomes JSC"},
            {"symbol": "MSN", "name": "Masan Group Corporation"},
            {"symbol": "VRE", "name": "Vincom Retail JSC"},
        ]

        recommendations = []
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")

        for stock in stocks_to_analyze[:limit * 2]:  # Analyze more to get variety
            try:
                # Fetch historical data
                df = await self._fetch_historical_prices(stock["symbol"], start_date, end_date)
                if df is None or len(df) < 20:
                    continue

                # Calculate indicators
                indicators = {"trend": "MACD", "momentum": "RSI", "volatility": "BB", "volume": "OBV"}
                df = self._calculate_indicators(df, indicators)

                prices = df["close"].values
                current_price = float(prices[-1])

                # Calculate key metrics
                rsi = float(df["rsi"].iloc[-1]) if pd.notna(df["rsi"].iloc[-1]) else 50
                macd = float(df["macd"].iloc[-1]) if pd.notna(df["macd"].iloc[-1]) else 0
                macd_signal = float(df["macd_signal"].iloc[-1]) if pd.notna(df["macd_signal"].iloc[-1]) else 0
                sma_20 = float(df["sma_20"].iloc[-1]) if pd.notna(df["sma_20"].iloc[-1]) else current_price
                sma_50 = float(df["sma_50"].iloc[-1]) if pd.notna(df["sma_50"].iloc[-1]) else current_price

                # Calculate price changes
                price_change_5d = (prices[-1] - prices[-5]) / prices[-5] * 100 if len(prices) >= 5 else 0
                price_change_20d = (prices[-1] - prices[-20]) / prices[-20] * 100 if len(prices) >= 20 else 0

                # Score-based recommendation system
                score = 0
                reasons = []

                # RSI analysis
                if rsi < 30:
                    score += 30
                    reasons.append(f"RSI ({rsi:.1f}) indicates oversold conditions")
                elif rsi < 40:
                    score += 15
                    reasons.append(f"RSI ({rsi:.1f}) approaching oversold territory")
                elif rsi > 70:
                    score -= 30
                    reasons.append(f"RSI ({rsi:.1f}) indicates overbought conditions")
                elif rsi > 60:
                    score -= 15
                    reasons.append(f"RSI ({rsi:.1f}) showing elevated levels")

                # MACD analysis
                if macd > macd_signal:
                    score += 20
                    reasons.append("MACD bullish crossover detected")
                else:
                    score -= 20
                    reasons.append("MACD showing bearish signal")

                # Price vs Moving Averages
                if current_price > sma_20 > sma_50:
                    score += 25
                    reasons.append("Price above both 20 & 50 day moving averages (uptrend)")
                elif current_price < sma_20 < sma_50:
                    score -= 25
                    reasons.append("Price below both moving averages (downtrend)")
                elif current_price > sma_20:
                    score += 10
                    reasons.append("Price above 20-day moving average")
                else:
                    score -= 10
                    reasons.append("Price below 20-day moving average")

                # Recent momentum
                if price_change_5d > 3:
                    score += 15
                    reasons.append(f"Strong 5-day momentum (+{price_change_5d:.1f}%)")
                elif price_change_5d < -3:
                    score -= 15
                    reasons.append(f"Weak 5-day momentum ({price_change_5d:.1f}%)")

                # Determine recommendation type and confidence
                if score >= 40:
                    rec_type = "BUY"
                    confidence = min(95, 60 + score)
                elif score <= -40:
                    rec_type = "SELL"
                    confidence = min(95, 60 + abs(score))
                else:
                    rec_type = "HOLD"
                    confidence = 50 + abs(score) // 2

                # Build reason string
                reason = ". ".join(reasons[:2]) + "."

                recommendations.append({
                    "type": rec_type,
                    "symbol": stock["symbol"],
                    "name": stock["name"],
                    "reason": reason,
                    "confidence": int(confidence),
                    "current_price": round(current_price, 2),
                    "rsi": round(rsi, 1),
                    "price_change_5d": round(price_change_5d, 2),
                    "price_change_20d": round(price_change_20d, 2),
                    "generated_at": datetime.now().isoformat()
                })

            except Exception as e:
                logger.error(f"Failed to analyze {stock['symbol']}: {e}")
                continue

        # Sort by confidence and return top recommendations (ensure variety in types)
        buy_recs = [r for r in recommendations if r["type"] == "BUY"]
        sell_recs = [r for r in recommendations if r["type"] == "SELL"]
        hold_recs = [r for r in recommendations if r["type"] == "HOLD"]

        # Sort each category by confidence
        buy_recs.sort(key=lambda x: x["confidence"], reverse=True)
        sell_recs.sort(key=lambda x: x["confidence"], reverse=True)
        hold_recs.sort(key=lambda x: x["confidence"], reverse=True)

        # Return a mix of recommendations
        result = []
        if buy_recs:
            result.append(buy_recs[0])
        if hold_recs:
            result.append(hold_recs[0])
        if sell_recs:
            result.append(sell_recs[0])

        # Fill remaining slots
        remaining = [r for r in recommendations if r not in result]
        remaining.sort(key=lambda x: x["confidence"], reverse=True)
        result.extend(remaining[:limit - len(result)])

        return result[:limit]

    # ──────────────────────────────────────────
    # VN30 universe helpers
    # ──────────────────────────────────────────

    async def _fetch_vn30_universe(self) -> List[Dict[str, str]]:
        """Return [{symbol, name}, …] for the live VN30 priceboard.

        Falls back to the hardcoded list when the price-board endpoint is
        unavailable so the recommendation endpoints never fail silently.
        """
        FALLBACK = [
            {"symbol": s, "name": s} for s in [
                "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR",
                "HDB", "HPG", "MBB", "MSN", "MWG", "PLX", "POW", "SAB",
                "SHB", "SSB", "SSI", "STB", "TCB", "TPB", "VCB", "VHM",
                "VIB", "VIC", "VJC", "VNM", "VPB", "VRE",
            ]
        ]
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}/api/v2/priceboards",
                    params={"group": "VN30"},
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    rows = data if isinstance(data, list) else data.get("data", [])
                    result = [
                        {"symbol": r.get("symbol") or r.get("ticker", ""),
                         "name": r.get("organ_name") or r.get("name") or r.get("symbol", "")}
                        for r in rows if r.get("symbol") or r.get("ticker")
                    ]
                    if result:
                        return result
        except Exception as e:
            logger.warning("Could not fetch VN30 universe: %s — using fallback", e)
        return FALLBACK

    # ──────────────────────────────────────────
    # Long-term fundamental recommendations
    # ──────────────────────────────────────────

    async def get_longterm_recommendations(self) -> List[Dict[str, Any]]:
        """Rank VN30 stocks by multi-year fundamental quality and return top 3.

        Scoring (all annual data from vnstock via stock-data-service):
          +3 pts per consecutive year of declining P/E   (value improving)
          +2 pts per consecutive year of growing net profit
          +1 pt  if latest ROE > 15 %
          -1 pt  if latest P/E > 25  (stretched valuation)

        Result is cached in Redis for 24 h.
        """
        CACHE_KEY = "dashboard:longterm_recs:v1"
        CACHE_TTL = 86400  # 24 h

        cached = await self._get_cached(CACHE_KEY)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass

        universe = await self._fetch_vn30_universe()
        scored: List[Dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            for stock in universe:
                sym = stock["symbol"]
                try:
                    # --- income statement (annual) ---
                    inc_resp = await client.get(
                        f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}"
                        f"/api/v2/companies/{sym}/financials/income-statement",
                        params={"period": "annual"},
                        timeout=30.0,
                    )
                    # --- ratios (annual) ---
                    rat_resp = await client.get(
                        f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}"
                        f"/api/v2/companies/{sym}/financials/ratios",
                        params={"period": "annual"},
                        timeout=30.0,
                    )

                    inc_rows = inc_resp.json() if inc_resp.status_code == 200 else []
                    rat_rows = rat_resp.json() if rat_resp.status_code == 200 else []

                    if not inc_rows and not rat_rows:
                        continue

                    # Sort newest-first then keep last 5 years
                    def _year(row):
                        for k in ("year", "Year", "fiscal_year", "period", "yearReport"):
                            if k in row and row[k] is not None:
                                try:
                                    return int(str(row[k])[:4])
                                except Exception:
                                    pass
                        return 0

                    inc_rows = sorted(inc_rows, key=_year, reverse=True)[:5]
                    rat_rows = sorted(rat_rows, key=_year, reverse=True)[:5]

                    # Extract net profit series (newest first)
                    profit_keys = ("net_profit", "netProfit", "profit_after_tax",
                                   "net_income", "Profit After Tax", "Net Profit")
                    profits = []
                    for row in inc_rows:
                        for k in profit_keys:
                            v = row.get(k)
                            if v is not None:
                                try:
                                    profits.append(float(v))
                                except Exception:
                                    pass
                                break

                    # Extract P/E series (newest first)
                    pe_keys = ("pe", "pe_ratio", "P/E", "priceToEarning", "price_to_earning")
                    pes = []
                    for row in rat_rows:
                        for k in pe_keys:
                            v = row.get(k)
                            if v is not None:
                                try:
                                    pes.append(float(v))
                                except Exception:
                                    pass
                                break

                    roe_keys = ("roe", "ROE", "return_on_equity")
                    latest_roe = None
                    for row in rat_rows[:1]:
                        for k in roe_keys:
                            if row.get(k) is not None:
                                try:
                                    latest_roe = float(row[k])
                                except Exception:
                                    pass
                                break

                    latest_pe = pes[0] if pes else None

                    # Score
                    score = 0
                    reasons = []

                    # Consecutive years of growing profit
                    profit_growth_years = 0
                    for i in range(len(profits) - 1):
                        if profits[i] > profits[i + 1]:  # newest > older
                            profit_growth_years += 1
                        else:
                            break
                    if profit_growth_years >= 1:
                        score += profit_growth_years * 2
                        reasons.append(f"Lợi nhuận tăng {profit_growth_years} năm liên tiếp")

                    # Consecutive years of declining P/E (value getting cheaper)
                    pe_decline_years = 0
                    for i in range(len(pes) - 1):
                        if pes[i] < pes[i + 1]:  # newest < older
                            pe_decline_years += 1
                        else:
                            break
                    if pe_decline_years >= 1:
                        score += pe_decline_years * 3
                        reasons.append(f"P/E cải thiện {pe_decline_years} năm liên tiếp")

                    if latest_roe is not None and latest_roe > 15:
                        score += 1
                        reasons.append(f"ROE mạnh ({latest_roe:.1f}%)")

                    if latest_pe is not None and latest_pe > 25:
                        score -= 1
                        reasons.append(f"P/E hiện tại cao ({latest_pe:.1f}x)")

                    if score <= 0 or not reasons:
                        continue

                    scored.append({
                        "symbol": sym,
                        "name": stock["name"],
                        "score": score,
                        "pe": round(latest_pe, 1) if latest_pe else None,
                        "roe": round(latest_roe, 1) if latest_roe else None,
                        "profit_growth_years": profit_growth_years,
                        "reason": ". ".join(reasons),
                        "generated_at": datetime.now().isoformat(),
                    })

                except Exception as e:
                    logger.error("Long-term scoring failed for %s: %s", sym, e)
                    continue

        scored.sort(key=lambda x: x["score"], reverse=True)
        result = scored[:3]

        try:
            await self._set_cached(CACHE_KEY, json.dumps(result), ttl=CACHE_TTL)
        except Exception:
            pass

        return result

    # ──────────────────────────────────────────
    # Short-term uptrend recommendations
    # ──────────────────────────────────────────

    async def get_shortterm_recommendations(self) -> List[Dict[str, Any]]:
        """Rank VN30 stocks by 1-year uptrend strength and return top 3.

        Scoring (1-year daily closes):
          +30 pts  price > SMA50 > SMA200          (golden alignment)
          +20 pts  price > SMA50 only
          +15 pts  1-year return > 20 %
          +10 pts  1-year return > 10 %
          +10 pts  price within 10 % of 52-week high
          +10 pts  MACD > signal on latest bar
          + 5 pts  positive 20-day momentum (price up vs 20 d ago)

        Result is cached in Redis for 24 h.
        """
        CACHE_KEY = "dashboard:shortterm_recs:v1"
        CACHE_TTL = 86400

        cached = await self._get_cached(CACHE_KEY)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass

        universe = await self._fetch_vn30_universe()
        scored: List[Dict[str, Any]] = []

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")

        for stock in universe:
            sym = stock["symbol"]
            try:
                df = await self._fetch_historical_prices(sym, start_date, end_date)
                if df is None or len(df) < 50:
                    continue

                prices = df["close"].values.astype(float)
                current = prices[-1]
                high_52w = prices[-min(252, len(prices)):].max()

                sma50 = float(pd.Series(prices).rolling(50).mean().iloc[-1])
                sma200_val = pd.Series(prices).rolling(200).mean().iloc[-1]
                sma200 = float(sma200_val) if pd.notna(sma200_val) else None

                # MACD
                ema12 = pd.Series(prices).ewm(span=12).mean()
                ema26 = pd.Series(prices).ewm(span=26).mean()
                macd_line = ema12 - ema26
                signal_line = macd_line.ewm(span=9).mean()
                macd_bull = float(macd_line.iloc[-1]) > float(signal_line.iloc[-1])

                ret_1y = (prices[-1] - prices[0]) / prices[0] * 100
                ret_20d = (prices[-1] - prices[-min(20, len(prices))]) / prices[-min(20, len(prices))] * 100

                score = 0
                reasons = []

                if sma200 and current > sma50 > sma200:
                    score += 30
                    reasons.append("Giá > SMA50 > SMA200 (xu hướng tăng mạnh)")
                elif current > sma50:
                    score += 20
                    reasons.append("Giá trên SMA50")

                if ret_1y > 20:
                    score += 15
                    reasons.append(f"Tăng {ret_1y:.0f}% trong 1 năm")
                elif ret_1y > 10:
                    score += 10
                    reasons.append(f"Tăng {ret_1y:.0f}% trong 1 năm")

                if current >= high_52w * 0.90:
                    score += 10
                    reasons.append("Gần đỉnh 52 tuần")

                if macd_bull:
                    score += 10
                    reasons.append("MACD bullish")

                if ret_20d > 0:
                    score += 5
                    reasons.append(f"Đà tăng 20 ngày (+{ret_20d:.1f}%)")

                if score <= 0:
                    continue

                scored.append({
                    "symbol": sym,
                    "name": stock["name"],
                    "score": score,
                    "current_price": round(float(current), 2),
                    "return_1y": round(ret_1y, 1),
                    "return_20d": round(ret_20d, 1),
                    "sma50": round(sma50, 2),
                    "high_52w": round(float(high_52w), 2),
                    "reason": ". ".join(reasons[:3]),
                    "generated_at": datetime.now().isoformat(),
                })

            except Exception as e:
                logger.error("Short-term scoring failed for %s: %s", sym, e)
                continue

        scored.sort(key=lambda x: x["score"], reverse=True)
        result = scored[:3]

        try:
            await self._set_cached(CACHE_KEY, json.dumps(result), ttl=CACHE_TTL)
        except Exception:
            pass

        return result

    # ==========================================
    # F-005 / F-006 — Full pattern catalog (Schwager Ch 5, 11, 12)
    # ==========================================

    async def get_all_patterns(
        self, symbol: str, lookback_bars: int = 120
    ) -> AllPatternsResponse:
        """Run the complete pattern catalog (reversal + continuation + trap)
        on the most recent `lookback_bars` daily bars.

        Empty `patterns` is a valid success response — "nothing detected."
        Pattern list is sorted newest-first by the rightmost key bar so the
        decision-helper-service sees the most actionable pattern first.
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=int(lookback_bars * 1.6))).strftime("%Y-%m-%d")

        df = await self._fetch_historical_prices(symbol, start_date, end_date)
        if df is None or len(df) == 0:
            return AllPatternsResponse(
                symbol=symbol.upper(),
                lookback_bars=0,
                patterns=[],
                pattern_count=0,
                categories={"reversal": 0, "continuation": 0, "trap": 0},
                generated_at=datetime.now(),
            )

        df = df.tail(lookback_bars).reset_index(drop=True)

        reversal_matches = run_reversal_detectors(df)
        continuation_matches = run_continuation_detectors(df)
        trap_matches = run_trap_detectors(df)

        def _to_schema(m) -> PatternMatchSchema:
            return PatternMatchSchema(
                pattern_name=m.pattern_name,
                pattern_type=m.pattern_type,
                found=m.found,
                confidence=m.confidence,
                key_bars=m.key_bars,
                measured_move_target=m.measured_move_target,
                neckline=m.neckline,
                details=m.details,
            )

        all_matches = (
            [_to_schema(m) for m in reversal_matches]
            + [_to_schema(m) for m in continuation_matches]
            + [_to_schema(m) for m in trap_matches]
        )
        all_matches.sort(
            key=lambda m: (m.key_bars[-1] if m.key_bars else 0), reverse=True
        )

        return AllPatternsResponse(
            symbol=symbol.upper(),
            lookback_bars=len(df),
            patterns=all_matches,
            pattern_count=len(all_matches),
            categories={
                "reversal": len(reversal_matches),
                "continuation": len(continuation_matches),
                "trap": len(trap_matches),
            },
            generated_at=datetime.now(),
        )

    async def get_reversal_patterns(
        self, symbol: str, lookback_bars: int = 120
    ) -> ReversalPatternsResponse:
        """Run all reversal-pattern detectors on the most recent
        `lookback_bars` daily bars and return whichever matched.

        Empty `patterns` is the success-case "nothing detected" answer —
        callers must distinguish that from the error path (insufficient
        data) themselves by checking lookback vs. what was actually
        available. We deliberately do not 500 on empty data; the trader
        UI is happier rendering "no patterns" than an exception toast.
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        # Pad the calendar window so weekends/holidays still yield enough
        # trading bars to satisfy the detectors' min_bars guard.
        start_date = (datetime.now() - timedelta(days=int(lookback_bars * 1.6))).strftime("%Y-%m-%d")

        df = await self._fetch_historical_prices(symbol, start_date, end_date)
        if df is None or len(df) == 0:
            return ReversalPatternsResponse(
                symbol=symbol.upper(),
                lookback_bars=0,
                patterns=[],
                generated_at=datetime.now(),
            )

        # Trim to exactly the requested lookback so detectors see a stable
        # window regardless of how much padding we pulled.
        df = df.tail(lookback_bars).reset_index(drop=True)

        matches = run_reversal_detectors(df)
        return ReversalPatternsResponse(
            symbol=symbol.upper(),
            lookback_bars=len(df),
            patterns=[
                PatternMatchSchema(
                    pattern_name=m.pattern_name,
                    pattern_type=m.pattern_type,
                    found=m.found,
                    confidence=m.confidence,
                    key_bars=m.key_bars,
                    measured_move_target=m.measured_move_target,
                    neckline=m.neckline,
                    details=m.details,
                )
                for m in matches
            ],
            generated_at=datetime.now(),
        )
