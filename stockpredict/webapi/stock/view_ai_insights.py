"""
AI Insights Views
Django REST API endpoints for AI-driven stock analysis.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from datetime import datetime, timedelta
import json
import traceback

from services.ai_insights_service import AIInsightsService
from services.advanced_technical_indicators import AdvancedTechnicalIndicators
from core.decorators import validate_input
from core.exceptions import ExternalServiceException


# Initialize services
ai_service = AIInsightsService()
indicators_service = AdvancedTechnicalIndicators()


@api_view(['GET'])
def get_ai_insights_overview(request):
    """
    Get overview of AI Insights capabilities and available indicators.
    """
    try:
        available_indicators = indicators_service.get_available_indicators()

        response_data = {
            'status': 'success',
            'data': {
                'ai_capabilities': {
                    'pattern_recognition': {
                        'description': 'Advanced chart pattern recognition using machine learning',
                        'features': [
                            'Candlestick pattern detection',
                            'Technical indicator patterns',
                            'Price action analysis',
                            'Support/resistance identification'
                        ]
                    },
                    'sentiment_analysis': {
                        'description': 'Market sentiment analysis from news and social media',
                        'features': [
                            'News sentiment scoring',
                            'Social media sentiment tracking',
                            'Market mood assessment',
                            'Confidence level calculation'
                        ]
                    },
                    'risk_assessment': {
                        'description': 'Comprehensive risk evaluation and management',
                        'features': [
                            'Volatility analysis',
                            'Beta calculation',
                            'Value at Risk (VaR)',
                            'Risk factor identification'
                        ]
                    },
                    'price_prediction': {
                        'description': 'ML-powered price forecasting with multiple models',
                        'features': [
                            'Random Forest regression',
                            'XGBoost prediction',
                            'Technical indicator integration',
                            'Confidence intervals'
                        ]
                    }
                },
                'available_indicators': available_indicators,
                'indicator_categories': indicators_service.get_indicator_categories()
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to get AI insights overview: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def get_comprehensive_ai_analysis(request):
    """
    Get comprehensive AI analysis including pattern recognition, sentiment analysis,
    risk assessment, and price prediction.

    Request body:
    {
        "symbol": "VIC",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "selected_indicators": {
            "trend": "MACD",
            "momentum": "RSI",
            "volatility": "BB",
            "volume": "OBV"
        }
    }
    """
    try:
        data = request.data

        # Validate required fields
        required_fields = ['symbol', 'selected_indicators']
        for field in required_fields:
            if field not in data:
                return Response({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }, status=status.HTTP_400_BAD_REQUEST)

        symbol = data['symbol'].upper()
        start_date = data.get('start_date', (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'))
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        selected_indicators = data['selected_indicators']

        # Validate selected indicators
        required_categories = ['trend', 'momentum', 'volatility', 'volume']
        for category in required_categories:
            if category not in selected_indicators:
                return Response({
                    'status': 'error',
                    'message': f'Missing indicator for category: {category}'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Get comprehensive insights
        insights = ai_service.get_comprehensive_insights(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            selected_indicators=selected_indicators
        )

        response_data = {
            'status': 'success',
            'data': {
                'symbol': symbol,
                'analysis_period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'selected_indicators': selected_indicators,
                'analysis_timestamp': datetime.now().isoformat(),
                'insights': insights
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except ExternalServiceException as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_502_BAD_GATEWAY)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to generate AI analysis: {str(e)}',
            'traceback': traceback.format_exc() if hasattr(request, 'debug') and request.debug else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def detect_patterns(request):
    """
    Detect chart patterns and technical analysis patterns.

    Request body:
    {
        "symbol": "VIC",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "indicators": ["MACD", "RSI", "BB"]
    }
    """
    try:
        data = request.data
        symbol = data.get('symbol', '').upper()
        start_date = data.get('start_date', (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'))
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        indicators = data.get('indicators', ['MACD', 'RSI', 'BB', 'OBV'])

        if not symbol:
            return Response({
                'status': 'error',
                'message': 'Symbol is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get stock data
        stock_data = indicators_service.get_price_data(symbol, start_date, end_date)

        # Calculate indicators
        indicators_data = indicators_service.calculate_multiple_indicators(
            symbol, indicators, start_date, end_date
        )

        # Detect patterns
        patterns = ai_service.detect_patterns(stock_data, indicators_data)

        response_data = {
            'status': 'success',
            'data': {
                'symbol': symbol,
                'analysis_period': {'start_date': start_date, 'end_date': end_date},
                'patterns': [pattern.__dict__ for pattern in patterns],
                'summary': ai_service._summarize_patterns(patterns),
                'pattern_count': len(patterns)
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Pattern detection failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def analyze_sentiment(request):
    """
    Analyze market sentiment for a stock.

    Request body:
    {
        "symbol": "VIC"
    }
    """
    try:
        data = request.data
        symbol = data.get('symbol', '').upper()

        if not symbol:
            return Response({
                'status': 'error',
                'message': 'Symbol is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        sentiment = ai_service.analyze_sentiment(symbol)

        response_data = {
            'status': 'success',
            'data': {
                'symbol': symbol,
                'sentiment': sentiment.__dict__,
                'analysis_timestamp': datetime.now().isoformat()
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Sentiment analysis failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def assess_risk(request):
    """
    Perform comprehensive risk assessment.

    Request body:
    {
        "symbol": "VIC",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }
    """
    try:
        data = request.data
        symbol = data.get('symbol', '').upper()
        start_date = data.get('start_date', (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'))
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))

        if not symbol:
            return Response({
                'status': 'error',
                'message': 'Symbol is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get stock data
        stock_data = indicators_service.get_price_data(symbol, start_date, end_date)

        # Assess risk
        risk = ai_service.assess_risk(stock_data, symbol)

        response_data = {
            'status': 'success',
            'data': {
                'symbol': symbol,
                'analysis_period': {'start_date': start_date, 'end_date': end_date},
                'risk_assessment': risk.__dict__,
                'analysis_timestamp': datetime.now().isoformat()
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Risk assessment failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def predict_prices(request):
    """
    Predict future prices using Random Forest and XGBoost models.

    Request body:
    {
        "symbol": "VIC",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "selected_indicators": {
            "trend": "MACD",
            "momentum": "RSI",
            "volatility": "BB",
            "volume": "OBV"
        }
    }
    """
    try:
        data = request.data
        symbol = data.get('symbol', '').upper()
        start_date = data.get('start_date', (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'))
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        selected_indicators = data.get('selected_indicators', {})

        if not symbol:
            return Response({
                'status': 'error',
                'message': 'Symbol is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not selected_indicators:
            return Response({
                'status': 'error',
                'message': 'Selected indicators are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get stock data
        stock_data = indicators_service.get_price_data(symbol, start_date, end_date)

        # Calculate indicators
        indicator_names = list(selected_indicators.values())
        indicators_data = indicators_service.calculate_multiple_indicators(
            symbol, indicator_names, start_date, end_date
        )

        # Predict prices
        predictions = ai_service.predict_prices(stock_data, indicators_data, selected_indicators)

        response_data = {
            'status': 'success',
            'data': {
                'symbol': symbol,
                'analysis_period': {'start_date': start_date, 'end_date': end_date},
                'selected_indicators': selected_indicators,
                'predictions': predictions,
                'analysis_timestamp': datetime.now().isoformat()
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Price prediction failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def calculate_technical_indicators(request):
    """
    Calculate multiple technical indicators.

    Request body:
    {
        "symbol": "VIC",
        "indicators": ["MACD", "RSI", "BB", "OBV"],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "custom_params": {
            "RSI": {"period": 21},
            "BB": {"period": 20, "std": 2.5}
        }
    }
    """
    try:
        data = request.data
        symbol = data.get('symbol', '').upper()
        indicators = data.get('indicators', [])
        start_date = data.get('start_date', (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'))
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        custom_params = data.get('custom_params', {})

        if not symbol:
            return Response({
                'status': 'error',
                'message': 'Symbol is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not indicators:
            return Response({
                'status': 'error',
                'message': 'At least one indicator is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Calculate indicators
        result = indicators_service.calculate_multiple_indicators(
            symbol, indicators, start_date, end_date, custom_params
        )

        response_data = {
            'status': 'success',
            'data': {
                'symbol': symbol,
                'analysis_period': {'start_date': start_date, 'end_date': end_date},
                'indicators': result,
                'calculation_timestamp': datetime.now().isoformat()
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Technical indicator calculation failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_available_indicators(request):
    """
    Get all available technical indicators grouped by category.
    """
    try:
        indicators = indicators_service.get_available_indicators()
        categories = indicators_service.get_indicator_categories()

        response_data = {
            'status': 'success',
            'data': {
                'indicators_by_category': indicators,
                'categories': categories,
                'total_indicators': sum(len(indicators[cat]) for cat in indicators)
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to get available indicators: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def get_ai_score(request):
    """
    Calculate overall AI confidence score based on multiple analysis factors.

    Request body:
    {
        "symbol": "VIC",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "selected_indicators": {
            "trend": "MACD",
            "momentum": "RSI",
            "volatility": "BB",
            "volume": "OBV"
        }
    }
    """
    try:
        data = request.data
        symbol = data.get('symbol', '').upper()
        start_date = data.get('start_date', (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'))
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        selected_indicators = data.get('selected_indicators', {})

        if not symbol:
            return Response({
                'status': 'error',
                'message': 'Symbol is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get comprehensive insights for scoring
        insights = ai_service.get_comprehensive_insights(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            selected_indicators=selected_indicators
        )

        response_data = {
            'status': 'success',
            'data': {
                'symbol': symbol,
                'analysis_period': {'start_date': start_date, 'end_date': end_date},
                'ai_score': insights.get('ai_score', {}),
                'analysis_timestamp': datetime.now().isoformat()
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'AI score calculation failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)