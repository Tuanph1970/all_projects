from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from services.stock_entity_service import MarketStockEntity
from services.stock_entities import StockService
from core.exceptions import ExternalServiceException, ValidationException
import logging
import numpy as np
import pandas as pd
import json

logger = logging.getLogger(__name__)


class NanInfEncoder(json.JSONEncoder):
    """Custom JSON encoder that converts NaN and Inf to null"""
    def encode(self, obj):
        if isinstance(obj, float):
            if np.isnan(obj) or np.isinf(obj):
                return 'null'
        return super().encode(obj)

    def iterencode(self, obj, _one_shot=False):
        """Encode object, converting NaN and Inf to null"""
        for chunk in super().iterencode(obj, _one_shot):
            # Replace JavaScript NaN and Infinity with null in the output
            chunk = chunk.replace('NaN', 'null')
            chunk = chunk.replace('Infinity', 'null')
            chunk = chunk.replace('-Infinity', 'null')
            yield chunk


def clean_nan_infinity(data):
    """
    Clean NaN and infinity values from data for JSON serialization
    """
    if isinstance(data, pd.DataFrame):
        # Replace NaN and infinity values with None
        data = data.replace([np.inf, -np.inf], None)
        data = data.where(pd.notna(data), None)
        return data.to_dict('records')
    elif isinstance(data, list):
        cleaned = []
        for item in data:
            if isinstance(item, dict):
                cleaned.append(clean_dict_values(item))
            else:
                cleaned.append(item)
        return cleaned
    elif isinstance(data, dict):
        return clean_dict_values(data)
    return data

def clean_dict_values(d):
    """
    Clean dictionary values for JSON serialization
    """
    cleaned = {}
    for k, v in d.items():
        if isinstance(v, (float, np.float64, np.float32)):
            if np.isnan(v) or np.isinf(v):
                cleaned[k] = None
            else:
                cleaned[k] = float(v)
        elif isinstance(v, (np.int64, np.int32)):
            cleaned[k] = int(v)
        elif isinstance(v, dict):
            cleaned[k] = clean_dict_values(v)
        elif isinstance(v, list):
            cleaned[k] = clean_nan_infinity(v)
        else:
            cleaned[k] = v
    return cleaned


@api_view(['GET', 'POST'])
def screen_stocks(request):
    """
    Stock screener API endpoint
    GET: Get default screened stocks
    POST: Screen stocks with custom criteria
    """
    if request.method == 'GET':
        try:
            # Default screening with basic criteria
            stock_service = StockService()
            screened_stocks = stock_service.screen_stocks(
                exchange="ALL",
                limit=50
            )

            # Convert to JSON format and clean NaN/infinity values
            result = clean_nan_infinity(screened_stocks) if not screened_stocks.empty else []

            # Use custom JSON encoder to handle NaN/Infinity values
            response_data = {
                'success': True,
                'data': result,
                'total': len(result)
            }

            # Manually encode with custom encoder and return as HttpResponse
            json_data = json.dumps(response_data, cls=NanInfEncoder)
            return HttpResponse(json_data, content_type='application/json')

        except Exception as e:
            logger.error(f"Error screening stocks (GET): {e}")
            return Response({
                'error': str(e),
                'success': False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'POST':
        try:
            data = request.data

            # Extract screening criteria
            exchange = data.get('exchange', 'ALL')

            # Convert numeric parameters to proper types, handling empty strings
            def safe_float_convert(value):
                """Convert value to float, return None for empty/invalid values"""
                if value is None or value == '' or value == 'null':
                    return None
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None

            def safe_int_convert(value, default=100):
                """Convert value to int, return default for empty/invalid values"""
                if value is None or value == '' or value == 'null':
                    return default
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return default

            min_price = safe_float_convert(data.get('min_price'))
            max_price = safe_float_convert(data.get('max_price'))
            min_volume = safe_float_convert(data.get('min_volume'))
            min_market_cap = safe_float_convert(data.get('min_market_cap'))
            limit = safe_int_convert(data.get('limit'), 100)

            stock_service = StockService()
            screened_stocks = stock_service.screen_stocks(
                exchange=exchange,
                min_price=min_price,
                max_price=max_price,
                min_volume=min_volume,
                min_market_cap=min_market_cap,
                limit=limit
            )

            # Convert to JSON format and clean NaN/infinity values
            result = clean_nan_infinity(screened_stocks) if not screened_stocks.empty else []

            # Use custom JSON encoder to handle NaN/Infinity values
            response_data = {
                'success': True,
                'data': result,
                'total': len(result),
                'criteria': {
                    'exchange': exchange,
                    'min_price': min_price,
                    'max_price': max_price,
                    'min_volume': min_volume,
                    'min_market_cap': min_market_cap,
                    'limit': limit
                }
            }

            # Manually encode with custom encoder and return as HttpResponse
            json_data = json.dumps(response_data, cls=NanInfEncoder)
            return HttpResponse(json_data, content_type='application/json')

        except KeyError as e:
            return Response({
                'error': f'Missing required field: {e}',
                'success': False
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error screening stocks (POST): {e}")
            return Response({
                'error': str(e),
                'success': False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_screening_criteria(request):
    """
    Get available screening criteria options
    """
    try:
        return Response({
            'success': True,
            'criteria': {
                'exchanges': ['ALL', 'HOSE', 'HNX', 'UPCOM'],
                'price_ranges': [
                    {'label': 'Under 10,000 VND', 'max_price': 10000},
                    {'label': '10,000 - 50,000 VND', 'min_price': 10000, 'max_price': 50000},
                    {'label': '50,000 - 100,000 VND', 'min_price': 50000, 'max_price': 100000},
                    {'label': 'Over 100,000 VND', 'min_price': 100000}
                ],
                'volume_ranges': [
                    {'label': 'High Volume', 'min_volume': 1000000},
                    {'label': 'Medium Volume', 'min_volume': 100000},
                    {'label': 'Low Volume', 'min_volume': 10000}
                ],
                'market_cap_ranges': [
                    {'label': 'Large Cap', 'min_market_cap': 10000000000000},  # 10 trillion VND
                    {'label': 'Mid Cap', 'min_market_cap': 1000000000000},    # 1 trillion VND
                    {'label': 'Small Cap', 'min_market_cap': 100000000000}    # 100 billion VND
                ]
            }
        })
    except Exception as e:
        logger.error(f"Error getting screening criteria: {e}")
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def advanced_stock_screen(request):
    """
    Advanced stock screening with multiple technical indicators
    """
    try:
        data = request.data

        # Convert numeric parameters to proper types, handling empty strings
        def safe_float_convert(value):
            """Convert value to float, return None for empty/invalid values"""
            if value is None or value == '' or value == 'null':
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        def safe_int_convert(value, default=50):
            """Convert value to int, return default for empty/invalid values"""
            if value is None or value == '' or value == 'null':
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default

        # Basic screening criteria
        exchange = data.get('exchange', 'ALL')
        min_price = safe_float_convert(data.get('min_price'))
        max_price = safe_float_convert(data.get('max_price'))
        min_volume = safe_float_convert(data.get('min_volume'))
        min_market_cap = safe_float_convert(data.get('min_market_cap'))
        limit = safe_int_convert(data.get('limit'), 50)

        # Technical analysis criteria
        include_technical = data.get('include_technical', False)

        stock_service = StockService()

        # Get basic screened stocks
        screened_stocks = stock_service.screen_stocks(
            exchange=exchange,
            min_price=min_price,
            max_price=max_price,
            min_volume=min_volume,
            min_market_cap=min_market_cap,
            limit=limit
        )

        result = []

        if not screened_stocks.empty:
            for _, stock in screened_stocks.iterrows():
                stock_data = stock.to_dict()

                # Add technical indicators if requested
                if include_technical and 'symbol' in stock_data:
                    try:
                        technical_data = stock_service.get_technical_indicators(
                            symbol=stock_data['symbol']
                        )
                        stock_data.update(technical_data)
                    except Exception as e:
                        logger.warning(f"Failed to get technical data for {stock_data.get('symbol', 'N/A')}: {e}")

                # Clean the stock data before appending
                cleaned_stock_data = clean_dict_values(stock_data)
                result.append(cleaned_stock_data)

        # Use custom JSON encoder to handle NaN/Infinity values
        response_data = {
            'success': True,
            'data': result,
            'total': len(result),
            'include_technical': include_technical
        }

        # Manually encode with custom encoder and return as HttpResponse
        json_data = json.dumps(response_data, cls=NanInfEncoder)
        return HttpResponse(json_data, content_type='application/json')

    except Exception as e:
        logger.error(f"Error in advanced stock screening: {e}")
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)