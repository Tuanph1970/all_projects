"""
Chatbot Agent View - Django REST Framework endpoints
Integrates with LLM-based agent routing system
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.core.cache import cache
import logging

from services.chatbot_agent_service import ChatbotAgentOrchestrator, QuestionCategory
from core.exceptions import ValidationException

logger = logging.getLogger(__name__)


# Initialize orchestrator (singleton pattern)
chatbot_orchestrator = ChatbotAgentOrchestrator()


@api_view(['POST'])
def ask_question(request):
    """
    Main endpoint for chatbot questions
    Routes questions through LLM agent system

    Request body:
    {
        "question": "What is the current VN-Index level?",
        "user_id": "optional_user_id"
    }

    Response:
    {
        "success": true,
        "data": {...},
        "message": "...",
        "category": "market_overview",
        "confidence": 0.95,
        "sources": ["..."],
        "metadata": {...}
    }
    """
    try:
        question = request.data.get('question')
        user_id = request.data.get('user_id') or request.user.id if hasattr(request, 'user') else None

        if not question:
            return Response(
                {
                    "success": False,
                    "message": "Question is required",
                    "error": "MISSING_QUESTION"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check cache for similar questions
        cache_key = f"chatbot_q_{hash(question.lower())}"
        cached_response = cache.get(cache_key)

        if cached_response:
            logger.info(f"Cache hit for question: {question[:50]}...")
            cached_response['metadata']['from_cache'] = True
            return Response(cached_response, status=status.HTTP_200_OK)

        # Process question through agent system
        agent_response = chatbot_orchestrator.process_question(question, user_id)

        # Convert to dict for JSON response
        response_data = {
            "success": agent_response.success,
            "data": agent_response.data,
            "message": agent_response.message,
            "category": agent_response.category.value,
            "confidence": agent_response.confidence,
            "sources": agent_response.sources,
            "metadata": agent_response.metadata
        }

        # Cache successful responses for 5 minutes
        if agent_response.success:
            cache.set(cache_key, response_data, timeout=300)

        logger.info(
            f"Question processed - Category: {agent_response.category.value}, "
            f"Success: {agent_response.success}, User: {user_id}"
        )

        return Response(response_data, status=status.HTTP_200_OK)

    except ValidationException as e:
        logger.warning(f"Validation error: {str(e)}")
        return Response(
            {
                "success": False,
                "message": str(e),
                "error": "VALIDATION_ERROR"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}", exc_info=True)
        return Response(
            {
                "success": False,
                "message": "An error occurred processing your question",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_capabilities(request):
    """
    Get chatbot capabilities and supported question types

    Response:
    {
        "categories": [...],
        "agents": [...],
        "sample_questions": [...]
    }
    """
    try:
        capabilities = chatbot_orchestrator.get_capabilities()
        return Response(capabilities, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error getting capabilities: {str(e)}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_question_categories(request):
    """
    Get all available question categories

    Response:
    {
        "categories": [
            {
                "name": "market_overview",
                "description": "Market indices and overview questions",
                "examples": [...]
            },
            ...
        ]
    }
    """
    try:
        categories_info = [
            {
                "name": QuestionCategory.MARKET_OVERVIEW.value,
                "description": "Market indices and overview questions",
                "examples": [
                    "What is the current VN-Index level?",
                    "How did the VN-Index perform today?",
                    "What's the trading volume on HOSE today?"
                ]
            },
            {
                "name": QuestionCategory.STOCK_PERFORMANCE.value,
                "description": "Individual stock performance and prices",
                "examples": [
                    "What's the current price of VCB stock?",
                    "Which stocks are gaining the most today?",
                    "Show me the top 10 stocks by trading volume"
                ]
            },
            {
                "name": QuestionCategory.SECTOR_ANALYSIS.value,
                "description": "Sector and industry analysis",
                "examples": [
                    "Which sectors are leading the market today?",
                    "How is the banking sector performing?",
                    "What's happening with real estate stocks?"
                ]
            },
            {
                "name": QuestionCategory.MARKET_TRENDS.value,
                "description": "Market trends and patterns",
                "examples": [
                    "Is the market in an uptrend or downtrend?",
                    "What's the market breadth today?",
                    "Are foreign investors buying or selling?"
                ]
            },
            {
                "name": QuestionCategory.TECHNICAL_INDICATORS.value,
                "description": "Technical analysis and indicators",
                "examples": [
                    "What's the RSI for VCB?",
                    "Show me the MACD for VNINDEX",
                    "Calculate 20-day moving average for HPG"
                ]
            },
            {
                "name": QuestionCategory.PREDICTIONS.value,
                "description": "Predictions and forecasts",
                "examples": [
                    "Will the market go up or down tomorrow?",
                    "What's the outlook for VN-Index this week?",
                    "Predict the price of VCB for next month"
                ]
            }
        ]

        return Response({"categories": categories_info}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def provide_feedback(request):
    """
    Collect user feedback on chatbot responses
    Used for continuous improvement

    Request body:
    {
        "question": "...",
        "response_helpful": true/false,
        "feedback_text": "optional feedback",
        "category": "market_overview"
    }
    """
    try:
        question = request.data.get('question')
        helpful = request.data.get('response_helpful')
        feedback_text = request.data.get('feedback_text', '')
        category = request.data.get('category')

        # Log feedback for analysis
        logger.info(
            f"Chatbot feedback - Question: {question[:50]}..., "
            f"Helpful: {helpful}, Category: {category}, Feedback: {feedback_text}"
        )

        # Store feedback in database (implement based on your needs)
        # feedback_repository.save_feedback(...)

        return Response(
            {"success": True, "message": "Thank you for your feedback!"},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Error saving feedback: {str(e)}", exc_info=True)
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint for chatbot service
    """
    try:
        # Test agent system
        test_response = chatbot_orchestrator.process_question("What is the current VN-Index level?")

        health_status = {
            "status": "healthy" if test_response.success or test_response.category != QuestionCategory.UNKNOWN else "degraded",
            "agents_count": len(chatbot_orchestrator.agents),
            "timestamp": test_response.metadata.get('timestamp')
        }

        return Response(health_status, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return Response(
            {"status": "unhealthy", "error": str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
