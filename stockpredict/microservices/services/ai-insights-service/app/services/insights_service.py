"""AI Insights Service - LLM Integration"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
import json
import logging
import redis.asyncio as redis

from app.config import get_settings
from app.models.schemas import (
    InsightType, InsightResponse, ComparisonResponse,
    NewsAnalysisResponse, QuestionResponse, MarketOverviewResponse
)

settings = get_settings()
logger = logging.getLogger(__name__)


class InsightsService:
    def __init__(self):
        self.redis_client = None
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
        """Call LLM API (OpenAI or fallback to template)"""
        if settings.OPENAI_API_KEY:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": settings.LLM_MODEL,
                            "messages": [
                                {"role": "system", "content": system_prompt or "You are a professional stock analyst."},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": settings.LLM_TEMPERATURE,
                            "max_tokens": settings.LLM_MAX_TOKENS
                        },
                        timeout=60.0
                    )
                    if response.status_code == 200:
                        return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"LLM API call failed: {e}")

        # Fallback to template-based response
        return self._generate_template_response(prompt)

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

        content = await self._call_llm(prompt)
        sentiment = self._analyze_sentiment(content)

        return NewsAnalysisResponse(
            symbol=symbol.upper(),
            overall_sentiment=sentiment,
            sentiment_score=0.5 if sentiment == "neutral" else (0.8 if sentiment == "bullish" else -0.8),
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
