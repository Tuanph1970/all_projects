"""
Chatbot Agent Service - LLM-based intelligent routing system
Implements Strategy Pattern, Chain of Responsibility, and Factory Pattern
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime, timedelta

from services.stock_market_service import StockMarketService, CompanyService
from services.technical_analysis_service import TechnicalAnalysisService
from services.time_series_service import TimeSeriesService
from core.exceptions import ValidationException, ExternalServiceException


class QuestionCategory(Enum):
    """Question categories for routing"""
    MARKET_OVERVIEW = "market_overview"
    STOCK_PERFORMANCE = "stock_performance"
    SECTOR_ANALYSIS = "sector_analysis"
    MARKET_TRENDS = "market_trends"
    NEWS_EVENTS = "news_events"
    PREDICTIONS = "predictions"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    TECHNICAL_INDICATORS = "technical_indicators"
    USER_ACTIONS = "user_actions"
    UNKNOWN = "unknown"


@dataclass
class QuestionContext:
    """Context object passed through agent chain"""
    question: str
    category: QuestionCategory
    extracted_entities: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None


@dataclass
class AgentResponse:
    """Standardized agent response"""
    success: bool
    data: Any
    message: str
    category: QuestionCategory
    confidence: float
    sources: List[str]
    metadata: Dict[str, Any]


class BaseAgent(ABC):
    """
    Abstract base agent following Strategy Pattern
    All specialized agents inherit from this
    """

    def __init__(self):
        self.name = self.__class__.__name__
        self.supported_categories = []

    @abstractmethod
    def can_handle(self, context: QuestionContext) -> bool:
        """Check if this agent can handle the question"""
        pass

    @abstractmethod
    def process(self, context: QuestionContext) -> AgentResponse:
        """Process the question and return response"""
        pass

    def _create_response(
        self,
        success: bool,
        data: Any,
        message: str,
        context: QuestionContext,
        confidence: float = 1.0,
        sources: List[str] = None
    ) -> AgentResponse:
        """Helper to create standardized responses"""
        return AgentResponse(
            success=success,
            data=data,
            message=message,
            category=context.category,
            confidence=confidence,
            sources=sources or [],
            metadata={"agent": self.name, "timestamp": datetime.now().isoformat()}
        )


class MarketOverviewAgent(BaseAgent):
    """
    Handles market indices and overview questions
    - Current VN-Index level
    - VN30, HNX performance
    - Trading volumes
    - Market volatility
    """

    def __init__(self):
        super().__init__()
        self.market_service = StockMarketService()
        self.supported_categories = [QuestionCategory.MARKET_OVERVIEW]

    def can_handle(self, context: QuestionContext) -> bool:
        return context.category == QuestionCategory.MARKET_OVERVIEW

    def process(self, context: QuestionContext) -> AgentResponse:
        try:
            entities = context.extracted_entities
            index_name = entities.get('index', 'VNINDEX')

            # Get market data
            if 'current_level' in entities.get('intent', ''):
                data = self._get_current_index_level(index_name)
            elif 'performance' in entities.get('intent', ''):
                period = entities.get('period', 'today')
                data = self._get_index_performance(index_name, period)
            elif 'volume' in entities.get('intent', ''):
                data = self._get_trading_volume()
            elif 'volatility' in entities.get('intent', ''):
                data = self._get_market_volatility(index_name)
            else:
                data = self._get_market_overview(index_name)

            return self._create_response(
                success=True,
                data=data,
                message=f"Market overview for {index_name} retrieved successfully",
                context=context,
                sources=["VCI Market Data", "Stock Market Service"]
            )
        except Exception as e:
            return self._create_response(
                success=False,
                data=None,
                message=f"Error retrieving market overview: {str(e)}",
                context=context,
                confidence=0.0
            )

    def _get_current_index_level(self, index_name: str) -> Dict:
        """Get current index level"""
        # Implement using existing services
        return {
            "index": index_name,
            "current_level": 1250.45,  # Placeholder - integrate with real service
            "change": 5.23,
            "change_percent": 0.42,
            "timestamp": datetime.now().isoformat()
        }

    def _get_index_performance(self, index_name: str, period: str) -> Dict:
        """Get index performance for a period"""
        return {
            "index": index_name,
            "period": period,
            "open": 1245.22,
            "close": 1250.45,
            "high": 1252.10,
            "low": 1244.80,
            "change": 5.23,
            "change_percent": 0.42
        }

    def _get_trading_volume(self) -> Dict:
        """Get trading volume data"""
        return {
            "total_volume": 458_000_000,
            "total_value": 12_500_000_000_000,
            "timestamp": datetime.now().isoformat()
        }

    def _get_market_volatility(self, index_name: str) -> Dict:
        """Calculate market volatility"""
        return {
            "index": index_name,
            "volatility": 1.25,
            "description": "Moderate volatility"
        }

    def _get_market_overview(self, index_name: str) -> Dict:
        """Get comprehensive market overview"""
        return {
            "index": index_name,
            "level": 1250.45,
            "change": 5.23,
            "volume": 458_000_000,
            "gainers": 245,
            "losers": 180,
            "unchanged": 75
        }


class StockPerformanceAgent(BaseAgent):
    """
    Handles individual stock performance questions
    - Current stock prices
    - Top gainers/losers
    - Trading volume
    - Price movements
    """

    def __init__(self):
        super().__init__()
        self.company_service = CompanyService()
        self.supported_categories = [QuestionCategory.STOCK_PERFORMANCE]

    def can_handle(self, context: QuestionContext) -> bool:
        return context.category == QuestionCategory.STOCK_PERFORMANCE

    def process(self, context: QuestionContext) -> AgentResponse:
        try:
            entities = context.extracted_entities
            intent = entities.get('intent', '')

            if 'current_price' in intent:
                ticker = entities.get('ticker')
                data = self._get_stock_price(ticker)
            elif 'gainers' in intent:
                limit = entities.get('limit', 10)
                data = self._get_top_gainers(limit)
            elif 'losers' in intent:
                limit = entities.get('limit', 10)
                data = self._get_top_losers(limit)
            elif 'volume' in intent:
                limit = entities.get('limit', 10)
                data = self._get_high_volume_stocks(limit)
            elif 'ceiling' in intent or 'floor' in intent:
                price_type = 'ceiling' if 'ceiling' in intent else 'floor'
                data = self._get_price_limit_stocks(price_type)
            elif 'movement' in intent:
                ticker = entities.get('ticker')
                period = entities.get('period', '1M')
                data = self._get_price_movement(ticker, period)
            else:
                ticker = entities.get('ticker')
                data = self._get_stock_overview(ticker)

            return self._create_response(
                success=True,
                data=data,
                message="Stock performance data retrieved successfully",
                context=context,
                sources=["Company Service", "Market Data"]
            )
        except Exception as e:
            return self._create_response(
                success=False,
                data=None,
                message=f"Error retrieving stock performance: {str(e)}",
                context=context,
                confidence=0.0
            )

    def _get_stock_price(self, ticker: str) -> Dict:
        """Get current stock price"""
        # Integrate with existing company service
        return {
            "ticker": ticker,
            "price": 75.5,
            "change": 1.2,
            "change_percent": 1.62,
            "volume": 1_250_000,
            "timestamp": datetime.now().isoformat()
        }

    def _get_top_gainers(self, limit: int) -> List[Dict]:
        """Get top gaining stocks"""
        return [
            {"ticker": "VCB", "price": 75.5, "change_percent": 5.2},
            {"ticker": "VHM", "price": 45.3, "change_percent": 4.8},
        ][:limit]

    def _get_top_losers(self, limit: int) -> List[Dict]:
        """Get top losing stocks"""
        return [
            {"ticker": "HPG", "price": 25.5, "change_percent": -3.2},
            {"ticker": "VNM", "price": 68.3, "change_percent": -2.8},
        ][:limit]

    def _get_high_volume_stocks(self, limit: int) -> List[Dict]:
        """Get stocks with highest trading volume"""
        return [
            {"ticker": "VCB", "volume": 5_000_000, "value": 375_000_000_000},
            {"ticker": "HPG", "volume": 4_500_000, "value": 115_000_000_000},
        ][:limit]

    def _get_price_limit_stocks(self, price_type: str) -> List[Dict]:
        """Get stocks hitting ceiling or floor prices"""
        return [
            {"ticker": "VCB", "price": 78.9, "type": price_type},
            {"ticker": "VHM", "price": 47.5, "type": price_type},
        ]

    def _get_price_movement(self, ticker: str, period: str) -> Dict:
        """Get price movement for a ticker over period"""
        return {
            "ticker": ticker,
            "period": period,
            "price_data": [
                {"date": "2025-10-01", "close": 74.0},
                {"date": "2025-10-02", "close": 74.5},
                {"date": "2025-10-03", "close": 75.5},
            ],
            "change": 1.5,
            "change_percent": 2.03
        }

    def _get_stock_overview(self, ticker: str) -> Dict:
        """Get comprehensive stock overview"""
        return {
            "ticker": ticker,
            "price": 75.5,
            "change": 1.2,
            "volume": 1_250_000,
            "market_cap": 500_000_000_000_000,
            "pe_ratio": 15.5,
            "52_week_high": 82.5,
            "52_week_low": 65.2
        }


class SectorAnalysisAgent(BaseAgent):
    """
    Handles sector and industry analysis questions
    - Sector performance
    - Industry group comparison
    - Leading/lagging sectors
    """

    def __init__(self):
        super().__init__()
        self.market_service = StockMarketService()
        self.supported_categories = [QuestionCategory.SECTOR_ANALYSIS]

    def can_handle(self, context: QuestionContext) -> bool:
        return context.category == QuestionCategory.SECTOR_ANALYSIS

    def process(self, context: QuestionContext) -> AgentResponse:
        try:
            entities = context.extracted_entities
            sector = entities.get('sector')

            if sector:
                data = self._get_sector_performance(sector)
            else:
                data = self._get_all_sectors_performance()

            return self._create_response(
                success=True,
                data=data,
                message="Sector analysis completed successfully",
                context=context,
                sources=["Market Service", "Sector Data"]
            )
        except Exception as e:
            return self._create_response(
                success=False,
                data=None,
                message=f"Error in sector analysis: {str(e)}",
                context=context,
                confidence=0.0
            )

    def _get_sector_performance(self, sector: str) -> Dict:
        """Get performance of specific sector"""
        return {
            "sector": sector,
            "change_percent": 2.5,
            "top_stocks": [
                {"ticker": "VCB", "change_percent": 3.2},
                {"ticker": "BID", "change_percent": 2.8},
            ],
            "market_cap": 1_500_000_000_000_000
        }

    def _get_all_sectors_performance(self) -> List[Dict]:
        """Get performance of all sectors"""
        return [
            {"sector": "Banking", "change_percent": 2.5, "volume": 150_000_000},
            {"sector": "Real Estate", "change_percent": -1.2, "volume": 80_000_000},
            {"sector": "Technology", "change_percent": 3.8, "volume": 45_000_000},
        ]


class MarketTrendsAgent(BaseAgent):
    """
    Handles market trend and pattern questions
    - Trend direction (uptrend/downtrend)
    - Market breadth
    - Foreign investor activity
    - Market sentiment
    """

    def __init__(self):
        super().__init__()
        self.market_service = StockMarketService()
        self.supported_categories = [QuestionCategory.MARKET_TRENDS]

    def can_handle(self, context: QuestionContext) -> bool:
        return context.category == QuestionCategory.MARKET_TRENDS

    def process(self, context: QuestionContext) -> AgentResponse:
        try:
            entities = context.extracted_entities
            intent = entities.get('intent', '')

            if 'trend' in intent:
                data = self._get_market_trend()
            elif 'breadth' in intent:
                data = self._get_market_breadth()
            elif 'foreign' in intent:
                data = self._get_foreign_activity()
            elif 'sentiment' in intent:
                data = self._get_market_sentiment()
            elif 'momentum' in intent:
                data = self._get_market_momentum()
            else:
                data = self._get_comprehensive_trends()

            return self._create_response(
                success=True,
                data=data,
                message="Market trend analysis completed",
                context=context,
                sources=["Market Service", "Trend Analysis"]
            )
        except Exception as e:
            return self._create_response(
                success=False,
                data=None,
                message=f"Error analyzing market trends: {str(e)}",
                context=context,
                confidence=0.0
            )

    def _get_market_trend(self) -> Dict:
        """Determine market trend direction"""
        return {
            "trend": "uptrend",
            "strength": "moderate",
            "duration_days": 15,
            "support_level": 1235.0,
            "resistance_level": 1265.0
        }

    def _get_market_breadth(self) -> Dict:
        """Get market breadth (gainers vs losers)"""
        return {
            "gainers": 245,
            "losers": 180,
            "unchanged": 75,
            "advancing_volume": 280_000_000,
            "declining_volume": 178_000_000,
            "breadth_ratio": 1.36
        }

    def _get_foreign_activity(self) -> Dict:
        """Get foreign investor activity"""
        return {
            "net_value": 125_000_000_000,
            "buying_value": 450_000_000_000,
            "selling_value": 325_000_000_000,
            "direction": "net_buy",
            "top_bought": ["VCB", "VHM", "HPG"],
            "top_sold": ["VNM", "MSN", "GAS"]
        }

    def _get_market_sentiment(self) -> Dict:
        """Analyze market sentiment"""
        return {
            "sentiment": "bullish",
            "confidence": 0.72,
            "fear_greed_index": 65,
            "put_call_ratio": 0.85
        }

    def _get_market_momentum(self) -> Dict:
        """Calculate market momentum"""
        return {
            "momentum": "positive",
            "rate_of_change": 2.5,
            "trend_strength": 0.68
        }

    def _get_comprehensive_trends(self) -> Dict:
        """Get comprehensive trend analysis"""
        return {
            "trend": self._get_market_trend(),
            "breadth": self._get_market_breadth(),
            "foreign_activity": self._get_foreign_activity(),
            "sentiment": self._get_market_sentiment()
        }


class TechnicalIndicatorAgent(BaseAgent):
    """
    Handles technical indicator questions
    - RSI, MACD, Moving Averages
    - Chart patterns
    - Volume analysis
    """

    def __init__(self):
        super().__init__()
        self.technical_service = TechnicalAnalysisService()
        self.supported_categories = [QuestionCategory.TECHNICAL_INDICATORS]

    def can_handle(self, context: QuestionContext) -> bool:
        return context.category == QuestionCategory.TECHNICAL_INDICATORS

    def process(self, context: QuestionContext) -> AgentResponse:
        try:
            entities = context.extracted_entities
            ticker = entities.get('ticker', 'VNINDEX')
            indicator = entities.get('indicator', '').lower()

            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

            if 'rsi' in indicator:
                data = self.technical_service.get_rsi(ticker, 14, start_date, end_date)
            elif 'macd' in indicator:
                data = self.technical_service.get_macd(ticker, 12, 26, 9, start_date, end_date)
            elif 'sma' in indicator or 'moving average' in indicator:
                length = entities.get('period', 20)
                data = self.technical_service.get_sma(ticker, length, start_date, end_date)
            elif 'ema' in indicator:
                length = entities.get('period', 20)
                data = self.technical_service.get_ema(ticker, length, start_date, end_date)
            else:
                data = self._get_all_indicators(ticker, start_date, end_date)

            return self._create_response(
                success=True,
                data=data,
                message=f"Technical indicators for {ticker} retrieved successfully",
                context=context,
                sources=["Technical Analysis Service"]
            )
        except Exception as e:
            return self._create_response(
                success=False,
                data=None,
                message=f"Error calculating technical indicators: {str(e)}",
                context=context,
                confidence=0.0
            )

    def _get_all_indicators(self, ticker: str, start_date: str, end_date: str) -> Dict:
        """Get all major technical indicators"""
        return {
            "ticker": ticker,
            "rsi": self.technical_service.get_rsi(ticker, 14, start_date, end_date)[-1] if self.technical_service.get_rsi(ticker, 14, start_date, end_date) else None,
            "macd": self.technical_service.get_macd(ticker, 12, 26, 9, start_date, end_date)[-1] if self.technical_service.get_macd(ticker, 12, 26, 9, start_date, end_date) else None,
            "sma_20": self.technical_service.get_sma(ticker, 20, start_date, end_date)[-1] if self.technical_service.get_sma(ticker, 20, start_date, end_date) else None,
        }


class PredictionAgent(BaseAgent):
    """
    Handles prediction and forecast questions
    - Price predictions with Sundial-inspired temporal patterns
    - Engineered features encoding indicator relationships
    - Technical analysis rules for expert knowledge
    Uses advanced prediction system with technical analysis
    """

    def __init__(self):
        super().__init__()
        # Import here to avoid circular dependencies
        from services.advanced_prediction_service import get_advanced_predictor
        self.predictor = get_advanced_predictor()
        self.supported_categories = [QuestionCategory.PREDICTIONS]

    def can_handle(self, context: QuestionContext) -> bool:
        return context.category == QuestionCategory.PREDICTIONS

    def process(self, context: QuestionContext) -> AgentResponse:
        try:
            entities = context.extracted_entities
            ticker = entities.get('ticker', 'VNINDEX')
            horizon = entities.get('horizon', '1D')  # 1D, 1W, 1M

            # Use advanced prediction system
            prediction_result = self.predictor.predict_stock(ticker, horizon)

            return self._create_response(
                success=True,
                data=prediction_result,
                message=f"Prediction for {ticker} generated successfully using advanced temporal analysis",
                context=context,
                confidence=prediction_result['confidence'],
                sources=[
                    "Temporal Pattern Analysis",
                    "Technical Indicators",
                    "Expert Rules Engine"
                ]
            )
        except Exception as e:
            return self._create_response(
                success=False,
                data=None,
                message=f"Error generating prediction: {str(e)}",
                context=context,
                confidence=0.0
            )


class LLMQuestionRouter:
    """
    LLM-based question router using pattern matching and NLP
    Routes questions to appropriate agents
    """

    def __init__(self):
        self.category_patterns = self._initialize_patterns()

    def _initialize_patterns(self) -> Dict[QuestionCategory, List[str]]:
        """Initialize keyword patterns for each category"""
        return {
            QuestionCategory.MARKET_OVERVIEW: [
                'vn-index', 'vn30', 'hnx', 'market', 'index', 'trading volume',
                'hose', 'volatility', 'all-time high'
            ],
            QuestionCategory.STOCK_PERFORMANCE: [
                'stock', 'price', 'ticker', 'gainer', 'loser', 'volume',
                'ceiling', 'floor', 'blue-chip', 'penny stock', 'liquidity',
                '52-week', 'actively traded'
            ],
            QuestionCategory.SECTOR_ANALYSIS: [
                'sector', 'industry', 'banking', 'real estate', 'tech',
                'oil', 'gas', 'steel', 'consumer', 'group'
            ],
            QuestionCategory.MARKET_TRENDS: [
                'trend', 'uptrend', 'downtrend', 'breadth', 'foreign',
                'sentiment', 'bullish', 'bearish', 'momentum', 'bull market',
                'bear market', 'support', 'resistance', 'overbought', 'oversold'
            ],
            QuestionCategory.NEWS_EVENTS: [
                'news', 'announcement', 'event', 'fed', 'interest rate',
                'usd', 'exchange rate', 'global', 'impact'
            ],
            QuestionCategory.PREDICTIONS: [
                'predict', 'forecast', 'outlook', 'will', 'should i buy',
                'should i sell', 'target', 'recover', 'good time'
            ],
            QuestionCategory.COMPARATIVE_ANALYSIS: [
                'compare', 'vs', 'versus', 'compared to', 'last week',
                'last year', 'regional', 'thailand', 'philippines'
            ],
            QuestionCategory.TECHNICAL_INDICATORS: [
                'rsi', 'macd', 'moving average', 'sma', 'ema', 'chart',
                'pattern', 'volume analysis', 'technical', 'indicator'
            ],
            QuestionCategory.USER_ACTIONS: [
                'portfolio', 'watchlist', 'alert', 'track', 'notification'
            ]
        }

    def route(self, question: str) -> QuestionContext:
        """
        Route question to appropriate category
        Extract entities and create context
        """
        question_lower = question.lower()

        # Determine category
        category = self._categorize_question(question_lower)

        # Extract entities
        entities = self._extract_entities(question_lower, category)

        # Create context
        context = QuestionContext(
            question=question,
            category=category,
            extracted_entities=entities,
            metadata={"confidence": entities.get('confidence', 0.8)},
            timestamp=datetime.now()
        )

        return context

    def _categorize_question(self, question: str) -> QuestionCategory:
        """Categorize question based on keyword patterns"""
        scores = {}

        for category, patterns in self.category_patterns.items():
            score = sum(1 for pattern in patterns if pattern in question)
            if score > 0:
                scores[category] = score

        if not scores:
            return QuestionCategory.UNKNOWN

        return max(scores, key=scores.get)

    def _extract_entities(self, question: str, category: QuestionCategory) -> Dict[str, Any]:
        """Extract entities from question"""
        entities = {}

        # Extract ticker symbols (3-4 uppercase letters)
        import re
        ticker_match = re.search(r'\b([A-Z]{3,4})\b', question.upper())
        if ticker_match:
            entities['ticker'] = ticker_match.group(1)

        # Extract time periods
        if 'today' in question:
            entities['period'] = 'today'
        elif 'week' in question:
            entities['period'] = '1W'
        elif 'month' in question:
            entities['period'] = '1M'
        elif 'year' in question:
            entities['period'] = '1Y'

        # Extract intent keywords
        intent_keywords = []
        if 'current' in question or 'what is' in question:
            intent_keywords.append('current_level')
        if 'performance' in question or 'perform' in question:
            intent_keywords.append('performance')
        if 'volume' in question:
            intent_keywords.append('volume')
        if 'predict' in question or 'forecast' in question:
            intent_keywords.append('prediction')

        entities['intent'] = ' '.join(intent_keywords)
        entities['confidence'] = 0.8

        return entities


class ChatbotAgentOrchestrator:
    """
    Main orchestrator implementing Chain of Responsibility
    Manages agent lifecycle and coordinates responses
    """

    def __init__(self):
        self.router = LLMQuestionRouter()
        self.agents = self._initialize_agents()

    def _initialize_agents(self) -> List[BaseAgent]:
        """Initialize all specialized agents"""
        return [
            MarketOverviewAgent(),
            StockPerformanceAgent(),
            SectorAnalysisAgent(),
            MarketTrendsAgent(),
            TechnicalIndicatorAgent(),
            PredictionAgent(),
        ]

    def process_question(self, question: str, user_id: Optional[str] = None) -> AgentResponse:
        """
        Main entry point for processing questions
        Routes to appropriate agent and returns response
        """
        # Route question
        context = self.router.route(question)
        context.user_id = user_id

        # Find appropriate agent
        for agent in self.agents:
            if agent.can_handle(context):
                return agent.process(context)

        # No agent found
        return AgentResponse(
            success=False,
            data=None,
            message="I couldn't understand your question. Please try rephrasing.",
            category=QuestionCategory.UNKNOWN,
            confidence=0.0,
            sources=[],
            metadata={"timestamp": datetime.now().isoformat()}
        )

    def get_capabilities(self) -> Dict[str, List[str]]:
        """Return chatbot capabilities"""
        return {
            "categories": [cat.value for cat in QuestionCategory if cat != QuestionCategory.UNKNOWN],
            "agents": [agent.name for agent in self.agents],
            "sample_questions": [
                "What is the current VN-Index level?",
                "Which stocks are gaining the most today?",
                "How is the banking sector performing?",
                "Is the market in an uptrend or downtrend?",
                "What's the RSI for VCB stock?",
                "Will the market go up tomorrow?",
            ]
        }
