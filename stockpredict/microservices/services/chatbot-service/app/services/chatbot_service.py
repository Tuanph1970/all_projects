"""Chatbot Service - Conversational AI"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import json
import re
import httpx
import logging
import redis.asyncio as redis

from app.config import get_settings
from app.models.schemas import (
    ChatResponse, Message, MessageRole, ConversationHistory,
    IntentType, DetectedIntent
)

settings = get_settings()
logger = logging.getLogger(__name__)


class ChatbotService:
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

    async def _get_session(self, session_id: str) -> Optional[Dict]:
        if self.redis_client:
            try:
                data = await self.redis_client.get(f"chat:{session_id}")
                if data:
                    return json.loads(data)
            except Exception:
                pass
        return None

    async def _save_session(self, session_id: str, data: Dict):
        if self.redis_client:
            try:
                ttl = settings.SESSION_TIMEOUT_MINUTES * 60
                await self.redis_client.set(f"chat:{session_id}", json.dumps(data, default=str), ex=ttl)
            except Exception:
                pass

    def _detect_intent(self, message: str) -> DetectedIntent:
        """Simple rule-based intent detection"""
        message_lower = message.lower()
        entities = {}

        # Extract stock symbols (Vietnamese stock symbols are typically 3 letters)
        symbols = re.findall(r'\b[A-Z]{3}\b', message.upper())
        if symbols:
            entities["symbols"] = symbols

        # Intent detection
        if any(word in message_lower for word in ["giá", "price", "bao nhiêu", "how much"]):
            return DetectedIntent(intent=IntentType.STOCK_PRICE, confidence=0.9, entities=entities)

        if any(word in message_lower for word in ["phân tích", "analysis", "đánh giá", "analyze"]):
            return DetectedIntent(intent=IntentType.STOCK_ANALYSIS, confidence=0.85, entities=entities)

        if any(word in message_lower for word in ["dự đoán", "predict", "forecast", "tương lai"]):
            return DetectedIntent(intent=IntentType.STOCK_PREDICTION, confidence=0.85, entities=entities)

        if any(word in message_lower for word in ["so sánh", "compare", "versus", "vs"]):
            return DetectedIntent(intent=IntentType.STOCK_COMPARISON, confidence=0.85, entities=entities)

        if any(word in message_lower for word in ["thị trường", "market", "vnindex", "hnx"]):
            return DetectedIntent(intent=IntentType.MARKET_OVERVIEW, confidence=0.8, entities=entities)

        if any(word in message_lower for word in ["danh mục", "portfolio", "cổ phiếu của tôi"]):
            return DetectedIntent(intent=IntentType.PORTFOLIO_QUERY, confidence=0.8, entities=entities)

        if any(word in message_lower for word in ["xin chào", "hello", "hi", "chào"]):
            return DetectedIntent(intent=IntentType.GREETING, confidence=0.95, entities=entities)

        if symbols:
            return DetectedIntent(intent=IntentType.STOCK_PRICE, confidence=0.7, entities=entities)

        return DetectedIntent(intent=IntentType.GENERAL_QUESTION, confidence=0.5, entities=entities)

    async def _fetch_stock_data(self, symbol: str) -> Dict:
        """Fetch stock data from services"""
        data = {}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.STOCK_DATA_SERVICE_URL}/{settings.API_PREFIX}/api/v2/stocks/{symbol}/quote",
                    timeout=30.0
                )
                if resp.status_code == 200:
                    data["quote"] = resp.json()
        except Exception as e:
            logger.error(f"Error fetching stock data: {e}")
        return data

    async def _get_analysis(self, symbol: str) -> Optional[Dict]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.ANALYSIS_SERVICE_URL}/{settings.API_PREFIX}/api/v2/analysis/technical/{symbol}",
                    timeout=30.0
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    async def _get_prediction(self, symbol: str) -> Optional[Dict]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.PREDICTION_SERVICE_URL}/{settings.API_PREFIX}/api/v2/predictions/predict/{symbol}",
                    timeout=30.0
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    async def _generate_response(self, intent: DetectedIntent, message: str, context: Dict) -> str:
        """Generate response based on intent"""
        symbols = intent.entities.get("symbols", [])

        if intent.intent == IntentType.GREETING:
            return "Xin chào! Tôi là trợ lý đầu tư chứng khoán. Bạn có thể hỏi tôi về giá cổ phiếu, phân tích kỹ thuật, dự đoán xu hướng, hoặc so sánh các mã cổ phiếu. Bạn cần hỗ trợ gì?"

        if intent.intent == IntentType.STOCK_PRICE and symbols:
            symbol = symbols[0]
            data = await self._fetch_stock_data(symbol)
            if data.get("quote"):
                q = data["quote"]
                return f"**{symbol}**: Giá hiện tại {q.get('price', 'N/A'):,.0f} VND, thay đổi {q.get('change_percent', 0):+.2f}%, khối lượng {q.get('volume', 0):,.0f}."
            return f"Không tìm thấy thông tin cho mã {symbol}."

        if intent.intent == IntentType.STOCK_ANALYSIS and symbols:
            symbol = symbols[0]
            analysis = await self._get_analysis(symbol)
            if analysis:
                return f"**Phân tích {symbol}**:\n- Tín hiệu: {analysis.get('overall_signal', 'N/A')}\n- RSI: {analysis.get('indicators', [{}])[0].get('value', 'N/A')}\n- Xu hướng: {analysis.get('trend', 'N/A')}"
            return f"Đang phân tích {symbol}..."

        if intent.intent == IntentType.STOCK_PREDICTION and symbols:
            symbol = symbols[0]
            prediction = await self._get_prediction(symbol)
            if prediction and prediction.get("predictions"):
                preds = prediction["predictions"][:3]
                lines = [f"**Dự đoán {symbol}** (5 ngày tới):"]
                for p in preds:
                    lines.append(f"- {p.get('date')}: {p.get('predicted_price', 0):,.0f} VND ({p.get('direction', 'N/A')})")
                return "\n".join(lines)
            return f"Đang tạo dự đoán cho {symbol}..."

        if intent.intent == IntentType.STOCK_COMPARISON and len(symbols) >= 2:
            results = []
            for s in symbols[:3]:
                data = await self._fetch_stock_data(s)
                if data.get("quote"):
                    results.append(f"- {s}: {data['quote'].get('price', 0):,.0f} VND ({data['quote'].get('change_percent', 0):+.2f}%)")
            if results:
                return "**So sánh cổ phiếu:**\n" + "\n".join(results)

        if intent.intent == IntentType.MARKET_OVERVIEW:
            return "**Thị trường hôm nay:** VN-Index đang giao dịch tích cực. Vui lòng xem chi tiết tại trang tổng quan thị trường."

        # General response
        if symbols:
            return f"Bạn muốn biết thêm thông tin gì về {', '.join(symbols)}? (giá, phân tích, dự đoán)"

        return "Tôi có thể giúp bạn tra cứu thông tin cổ phiếu. Vui lòng cho biết mã cổ phiếu bạn quan tâm (ví dụ: VNM, FPT, VIC)."

    async def chat(self, message: str, session_id: Optional[str] = None,
                  user_id: Optional[int] = None, context: Optional[Dict] = None) -> ChatResponse:
        """Process chat message and return response"""

        # Get or create session
        if not session_id:
            session_id = str(uuid.uuid4())

        session = await self._get_session(session_id) or {
            "messages": [],
            "context": context or {},
            "user_id": user_id,
            "created_at": datetime.now().isoformat()
        }

        # Detect intent
        intent = self._detect_intent(message)

        # Generate response
        response_text = await self._generate_response(intent, message, session.get("context", {}))

        # Update session
        session["messages"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        session["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })

        # Keep only last N messages
        if len(session["messages"]) > settings.MAX_CONVERSATION_HISTORY * 2:
            session["messages"] = session["messages"][-settings.MAX_CONVERSATION_HISTORY * 2:]

        session["last_activity"] = datetime.now().isoformat()

        # Save session
        await self._save_session(session_id, session)

        # Generate suggestions
        suggestions = self._generate_suggestions(intent)

        return ChatResponse(
            session_id=session_id,
            message=response_text,
            intent=intent.intent.value,
            entities=[{"type": k, "value": v} for k, v in intent.entities.items()],
            actions_taken=[],
            suggestions=suggestions,
            timestamp=datetime.now()
        )

    def _generate_suggestions(self, intent: DetectedIntent) -> List[str]:
        """Generate follow-up suggestions"""
        symbols = intent.entities.get("symbols", [])

        if intent.intent == IntentType.STOCK_PRICE and symbols:
            return [
                f"Phân tích kỹ thuật {symbols[0]}",
                f"Dự đoán giá {symbols[0]}",
                "Xem thị trường"
            ]

        if intent.intent == IntentType.GREETING:
            return ["Giá VNM", "Phân tích FPT", "Thị trường hôm nay"]

        return ["Tra giá cổ phiếu", "Phân tích kỹ thuật", "Dự đoán xu hướng"]

    async def get_history(self, session_id: str) -> Optional[ConversationHistory]:
        """Get conversation history"""
        session = await self._get_session(session_id)
        if not session:
            return None

        messages = [
            Message(
                role=MessageRole(m["role"]),
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"])
            )
            for m in session.get("messages", [])
        ]

        return ConversationHistory(
            session_id=session_id,
            messages=messages,
            created_at=datetime.fromisoformat(session.get("created_at", datetime.now().isoformat())),
            last_activity=datetime.fromisoformat(session.get("last_activity", datetime.now().isoformat()))
        )

    async def clear_session(self, session_id: str) -> bool:
        """Clear conversation session"""
        if self.redis_client:
            try:
                await self.redis_client.delete(f"chat:{session_id}")
                return True
            except Exception:
                pass
        return False
