from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from services.stock_entity_service import MarketStockEntity
from services.stock_entities import StockService
from core.exceptions import ExternalServiceException, ValidationException
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
def get_all_stocks(request):
    """
    Get comprehensive list of all stocks with filtering and pagination
    """
    try:
        # Get query parameters
        exchange = request.GET.get('exchange', None)
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 50))
        search = request.GET.get('search', '')
        sort_by = request.GET.get('sort_by', 'symbol')
        sort_order = request.GET.get('sort_order', 'asc')

        stock_service = StockService()

        # Get all stocks from the specified exchange or all exchanges
        all_stocks = stock_service.get_all_stocks(exchange=exchange)

        if all_stocks.empty:
            return Response({
                'success': True,
                'data': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0
            })

        # Apply search filter if provided
        if search:
            search_mask = (
                all_stocks['symbol'].str.contains(search, case=False, na=False) |
                all_stocks['name'].str.contains(search, case=False, na=False) if 'name' in all_stocks.columns
                else all_stocks['symbol'].str.contains(search, case=False, na=False)
            )
            all_stocks = all_stocks[search_mask]

        # Apply sorting
        if sort_by in all_stocks.columns:
            ascending = sort_order.lower() == 'asc'
            all_stocks = all_stocks.sort_values(by=sort_by, ascending=ascending)

        # Calculate pagination
        total_records = len(all_stocks)
        total_pages = (total_records + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        # Get paginated data
        paginated_stocks = all_stocks.iloc[start_idx:end_idx]

        # Convert to JSON format - replace NaN values with None for JSON compatibility
        result = paginated_stocks.fillna(value='').to_dict('records')

        return Response({
            'success': True,
            'data': result,
            'total': total_records,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'exchange': exchange,
            'search': search,
            'sort_by': sort_by,
            'sort_order': sort_order
        })

    except ValueError as e:
        return Response({
            'error': f'Invalid parameter: {e}',
            'success': False
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error getting stock list: {e}")
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_stocks_by_exchange(request, exchange):
    """
    Get stocks by specific exchange
    """
    try:
        stock_service = StockService()
        stocks = stock_service.get_all_stocks(exchange=exchange.upper())

        if stocks.empty:
            return Response({
                'success': True,
                'data': [],
                'total': 0,
                'exchange': exchange.upper()
            })

        result = stocks.fillna(value='').to_dict('records')

        return Response({
            'success': True,
            'data': result,
            'total': len(result),
            'exchange': exchange.upper()
        })

    except Exception as e:
        logger.error(f"Error getting stocks by exchange {exchange}: {e}")
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_stock_details(request, symbol):
    """
    Get detailed information for a specific stock
    """
    try:
        stock_service = StockService(symbol=symbol.upper())

        # Get basic company overview
        overview = stock_service.get_company_overview()

        # Get latest price data
        price_data = stock_service.get_price_history(
            start='2024-01-01',
            end='2024-12-31'
        )

        latest_price = {}
        if not price_data.empty:
            latest_row = price_data.iloc[-1]
            latest_price = {
                'current_price': latest_row.get('close', 0),
                'open_price': latest_row.get('open', 0),
                'high_price': latest_row.get('high', 0),
                'low_price': latest_row.get('low', 0),
                'volume': latest_row.get('volume', 0),
                'date': latest_row.get('time', '').strftime('%Y-%m-%d') if 'time' in latest_row else ''
            }

        # Get technical indicators
        technical_indicators = stock_service.get_technical_indicators()

        # Get financial ratios
        financial_ratios = stock_service.get_financial_ratios()
        latest_ratios = {}
        if not financial_ratios.empty:
            latest_ratios = financial_ratios.iloc[-1].to_dict()

        result = {
            'symbol': symbol.upper(),
            'overview': overview,
            'latest_price': latest_price,
            'technical_indicators': technical_indicators,
            'financial_ratios': latest_ratios
        }

        return Response({
            'success': True,
            'data': result
        })

    except Exception as e:
        logger.error(f"Error getting stock details for {symbol}: {e}")
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def get_multiple_stock_details(request):
    """
    Get details for multiple stocks at once
    """
    try:
        data = JSONParser().parse(request)
        symbols = data.get('symbols', [])

        if not symbols:
            return Response({
                'error': 'No symbols provided',
                'success': False
            }, status=status.HTTP_400_BAD_REQUEST)

        stock_service = StockService()
        result = []

        for symbol in symbols:
            try:
                # Analyze single stock
                analysis = stock_service.analyze_stock(symbol.upper())

                if not analysis.empty:
                    stock_data = analysis.iloc[0].fillna(value='').to_dict()
                    result.append(stock_data)
                else:
                    result.append({
                        'symbol': symbol.upper(),
                        'error': 'No data available'
                    })

            except Exception as e:
                logger.warning(f"Error analyzing {symbol}: {e}")
                result.append({
                    'symbol': symbol.upper(),
                    'error': str(e)
                })

        return Response({
            'success': True,
            'data': result,
            'total': len(result)
        })

    except Exception as e:
        logger.error(f"Error getting multiple stock details: {e}")
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_stock_search_suggestions(request):
    """
    Get stock search suggestions based on query
    """
    try:
        query = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', 10))

        if len(query) < 2:
            return Response({
                'success': True,
                'data': [],
                'query': query
            })

        stock_service = StockService()
        all_stocks = stock_service.get_all_stocks()

        if all_stocks.empty:
            return Response({
                'success': True,
                'data': [],
                'query': query
            })

        # Filter stocks based on query
        search_mask = (
            all_stocks['symbol'].str.contains(query, case=False, na=False) |
            (all_stocks['name'].str.contains(query, case=False, na=False) if 'name' in all_stocks.columns else False)
        )

        suggestions = all_stocks[search_mask].head(limit)
        result = suggestions[['symbol', 'name'] if 'name' in suggestions.columns else ['symbol']].fillna(value='').to_dict('records')

        return Response({
            'success': True,
            'data': result,
            'query': query,
            'total': len(result)
        })

    except Exception as e:
        logger.error(f"Error getting stock search suggestions: {e}")
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)