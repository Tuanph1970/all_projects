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

    # ------------------------------------------------------------------
    # Usage stats — Redis-backed counters powering GET /stats.
    #
    # Two granularities are kept side-by-side so /stats can answer any
    # period in O(constant) reads:
    #   * Daily counters at chatbot:stats:YYYY-MM-DD:* — used for today /
    #     week / month aggregations (summed at read time).
    #   * All-time counters at chatbot:stats:total:* — used for "all"
    #     directly, no aggregation needed.
    # All counters are best-effort: if Redis is down, /stats degrades
    # to zeros rather than failing.
    # ------------------------------------------------------------------
    async def _track_usage(
        self,
        intent_name: str,
        is_new_session: bool,
        response_ms: float,
    ) -> None:
        if not self.redis_client:
            return
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            daily = f"chatbot:stats:{today}"
            total = "chatbot:stats:total"

            pipe = self.redis_client.pipeline()
            pipe.incr(f"{daily}:messages")
            pipe.incr(f"{total}:messages")
            pipe.incrby(f"{daily}:response_ms_sum", int(response_ms))
            pipe.incrby(f"{total}:response_ms_sum", int(response_ms))
            pipe.incr(f"{daily}:response_count")
            pipe.incr(f"{total}:response_count")
            pipe.hincrby(f"{daily}:intents", intent_name, 1)
            pipe.hincrby(f"{total}:intents", intent_name, 1)
            if is_new_session:
                pipe.incr(f"{daily}:sessions")
                pipe.incr(f"{total}:sessions")
            # Keep daily counters for ~90 days so month aggregations stay
            # accurate and we don't grow Redis indefinitely.
            pipe.expire(f"{daily}:messages", 90 * 86400)
            pipe.expire(f"{daily}:response_ms_sum", 90 * 86400)
            pipe.expire(f"{daily}:response_count", 90 * 86400)
            pipe.expire(f"{daily}:intents", 90 * 86400)
            pipe.expire(f"{daily}:sessions", 90 * 86400)
            await pipe.execute()
        except Exception as e:
            logger.debug("Usage tracking failed (non-fatal): %s", e)

    async def get_usage_stats(self, period: str) -> Dict[str, Any]:
        """Aggregate usage stats over the requested period.

        Returns a dict matching the UsageStats schema. Falls back to zeros
        if Redis is unavailable so the endpoint stays up.
        """
        zero_stats = {
            "total_sessions": 0,
            "total_messages": 0,
            "avg_messages_per_session": 0.0,
            "top_intents": {},
            "avg_response_time_ms": 0.0,
            "satisfaction_rate": None,
        }
        if not self.redis_client:
            return zero_stats

        try:
            if period == "all":
                date_keys = ["chatbot:stats:total"]
            else:
                days = {"today": 1, "week": 7, "month": 30}.get(period, 1)
                today = datetime.utcnow().date()
                date_keys = [
                    f"chatbot:stats:{(today - timedelta(days=i)).isoformat()}"
                    for i in range(days)
                ]

            sessions = 0
            messages = 0
            response_ms_sum = 0
            response_count = 0
            intents: Dict[str, int] = {}
            for key in date_keys:
                pipe = self.redis_client.pipeline()
                pipe.get(f"{key}:sessions")
                pipe.get(f"{key}:messages")
                pipe.get(f"{key}:response_ms_sum")
                pipe.get(f"{key}:response_count")
                pipe.hgetall(f"{key}:intents")
                s, m, rs, rc, intent_map = await pipe.execute()
                sessions += int(s or 0)
                messages += int(m or 0)
                response_ms_sum += int(rs or 0)
                response_count += int(rc or 0)
                for name, count in (intent_map or {}).items():
                    intents[name] = intents.get(name, 0) + int(count)

            avg_messages = (messages / sessions) if sessions else 0.0
            avg_response_ms = (response_ms_sum / response_count) if response_count else 0.0
            top_intents = dict(
                sorted(intents.items(), key=lambda kv: kv[1], reverse=True)[:10]
            )
            return {
                "total_sessions": sessions,
                "total_messages": messages,
                "avg_messages_per_session": round(avg_messages, 2),
                "top_intents": top_intents,
                "avg_response_time_ms": round(avg_response_ms, 1),
                "satisfaction_rate": None,  # No feedback signal wired yet
            }
        except Exception as e:
            logger.warning("Failed to read usage stats: %s", e)
            return zero_stats

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
        import time
        start_time = time.perf_counter()

        # Get or create session
        if not session_id:
            session_id = str(uuid.uuid4())

        existing = await self._get_session(session_id)
        is_new_session = existing is None
        session = existing or {
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

        # Best-effort usage tracking — never blocks the response.
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        await self._track_usage(
            intent_name=intent.intent.value,
            is_new_session=is_new_session,
            response_ms=elapsed_ms,
        )

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
