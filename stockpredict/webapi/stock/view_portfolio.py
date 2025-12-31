from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
from decimal import Decimal
from repositories.portfolio_repository import PortfolioRepository
from repositories.authentication_repository import AuthenticationRepository
from repositories.alerts_repository import AlertsRepository
from services.stock_market_service import StockMarketService
from services.stock_data_sync_service import StockDataSyncService
import jwt
import os

logger = logging.getLogger(__name__)


def get_user_id_from_token(request):
    try:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        decoded = jwt.decode(token, 'secret_key', algorithms=['HS256'])
        return decoded.get('user_id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None


@csrf_exempt
@require_http_methods(["GET"])
def get_portfolio(request):
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        portfolio_repo = PortfolioRepository()
        portfolio_items = portfolio_repo.get_user_portfolio(user_id)
        
        formatted_portfolio = []
        for item in portfolio_items:
            formatted_item = {
                'symbol': item['symbol'],
                'name': item['company_name'],
                'shares': float(item['shares']),
                'avgPrice': float(item['avg_price']),
                'currentPrice': 0.0,  # Will be updated from external API
                'change': '+0.00%'  # Will be calculated based on current price
            }
            formatted_portfolio.append(formatted_item)
        
        return JsonResponse(formatted_portfolio, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def add_stock(request):
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        data = json.loads(request.body)
        symbol = data.get('symbol', '').upper()
        company_name = data.get('company_name', '')
        shares = Decimal(str(data.get('shares', 0)))
        price = Decimal(str(data.get('price', 0)))

        if not symbol or shares <= 0 or price <= 0:
            return JsonResponse({'error': 'Invalid data provided'}, status=400)

        # Trigger stock data sync for the new symbol
        sync_service = StockDataSyncService()
        sync_result = sync_service.sync_stock_data(symbol)

        if sync_result.status == 'error':
            # Log warning but continue - sync can happen later
            logger.warning(f"Initial sync failed for {symbol}: {sync_result.error_message}")

        # Add to portfolio
        portfolio_repo = PortfolioRepository()
        success = portfolio_repo.add_stock_to_portfolio(user_id, symbol, company_name, shares, price)

        if success:
            return JsonResponse({
                'message': 'Stock added successfully',
                'sync_status': sync_result.status,
                'records_synced': sync_result.records_added
            })
        else:
            return JsonResponse({'error': 'Failed to add stock'}, status=500)
    except Exception as e:
        logger.error(f"Error adding stock: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def buy_stock(request):
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        data = json.loads(request.body)
        symbol = data.get('symbol', '').upper()
        company_name = data.get('company_name', '')
        shares = Decimal(str(data.get('shares', 0)))
        price = Decimal(str(data.get('price', 0)))

        if not symbol or shares <= 0 or price <= 0:
            return JsonResponse({'error': 'Invalid data provided'}, status=400)

        # Trigger stock data sync for the symbol (will skip if already synced)
        sync_service = StockDataSyncService()
        sync_result = sync_service.sync_stock_data(symbol)

        if sync_result.status == 'error':
            logger.warning(f"Sync failed for {symbol}: {sync_result.error_message}")

        # Add to portfolio
        portfolio_repo = PortfolioRepository()
        success = portfolio_repo.add_stock_to_portfolio(user_id, symbol, company_name, shares, price)

        if success:
            return JsonResponse({
                'message': f'Successfully bought {shares} shares of {symbol}',
                'sync_status': sync_result.status,
                'records_synced': sync_result.records_added
            })
        else:
            return JsonResponse({'error': 'Failed to buy stock'}, status=500)
    except Exception as e:
        logger.error(f"Error buying stock: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def sell_stock(request):
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        data = json.loads(request.body)
        symbol = data.get('symbol', '').upper()
        shares = Decimal(str(data.get('shares', 0)))
        
        if not symbol or shares <= 0:
            return JsonResponse({'error': 'Invalid data provided'}, status=400)
        
        portfolio_repo = PortfolioRepository()
        success = portfolio_repo.sell_stock_from_portfolio(user_id, symbol, shares)
        
        if success:
            return JsonResponse({'message': f'Successfully sold {shares} shares of {symbol}'})
        else:
            return JsonResponse({'error': 'Failed to sell stock or insufficient shares'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def remove_stock(request):
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        symbol = request.GET.get('symbol', '').upper()
        
        if not symbol:
            return JsonResponse({'error': 'Symbol is required'}, status=400)
        
        portfolio_repo = PortfolioRepository()
        success = portfolio_repo.remove_stock_from_portfolio(user_id, symbol)
        
        if success:
            return JsonResponse({'message': f'Successfully removed {symbol} from portfolio'})
        else:
            return JsonResponse({'error': 'Failed to remove stock'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_portfolio_summary(request):
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        portfolio_repo = PortfolioRepository()
        summary = portfolio_repo.get_portfolio_summary(user_id)
        
        return JsonResponse(summary)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@csrf_exempt
@require_http_methods(["GET"])
def search_stocks(request):
    """
    API endpoint to search stocks by symbol or company name

    Query parameters:
        query (required): Search query for stock symbol or company name
        source (optional): Data source for stock data (default: VCI)

    Returns:
        JSON response containing list of matching stocks with symbol, name, and current price
    """
    try:
        # Get required query parameter
        query = request.GET.get('query', '').strip()

        if not query:
            return JsonResponse({'error': 'Query parameter is required'}, status=400)

        # Get optional source parameter from query string
        source = request.GET.get('source', 'VCI')

        # Initialize stock market service
        stock_service = StockMarketService()

        # Get all symbol and price data
        all_stocks_data = stock_service.get_symbol_and_price(source=source)

        # Filter stocks based on query (search in both symbol and company name)
        query_lower = query.lower()
        filtered_stocks = []

        for stock in all_stocks_data:
            symbol = stock.get('symbol', '').lower()
            name = stock.get('name', '').lower()

            # Check if query matches symbol or company name
            if query_lower in symbol or query_lower in name:
                formatted_stock = {
                    'symbol': stock.get('symbol', ''),
                    'name': stock.get('name', ''),
                    'price': stock.get('price', 0)
                }
                filtered_stocks.append(formatted_stock)

        # Limit results to prevent too many matches
        max_results = 20
        if len(filtered_stocks) > max_results:
            filtered_stocks = filtered_stocks[:max_results]

        return JsonResponse(filtered_stocks, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_stock_options(request):
    """
    API endpoint to get list of all stocks with their symbols and current prices
    
    Query parameters:
        source (optional): Data source for stock data (default: VCI)
    
    Returns:
        JSON response containing list of objects with symbol and current_price
    """
    try:
        # Get optional source parameter from query string
        source = request.GET.get('source', 'VCI')
        
        # Initialize stock market service
        stock_service = StockMarketService()
        
        # Get symbol and price data
        symbol_price_data = stock_service.get_symbol_and_price(source=source)
        
        return JsonResponse(symbol_price_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_portfolio_performance(request):
    """
    API endpoint to get detailed portfolio performance data with current prices
    
    Returns:
        JSON response containing portfolio items with current prices and performance metrics
    """
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        portfolio_repo = PortfolioRepository()
        stock_service = StockMarketService()
        
        # Get user's portfolio
        portfolio_items = portfolio_repo.get_user_portfolio(user_id)
        
        if not portfolio_items:
            return JsonResponse([], safe=False)
        
        # Get current market prices for all stocks
        market_data = stock_service.get_symbol_and_price(source='VCI')
        
        # Create a dictionary for quick lookup
        price_map = {item['symbol']: item.get('price', 0) for item in market_data}
        
        # Calculate performance metrics for each stock
        formatted_portfolio = []
        for item in portfolio_items:
            symbol = item['symbol']
            shares = float(item['shares'])
            avg_price = float(item['avg_price'])
            current_price = price_map.get(symbol, avg_price)  # Fallback to avg_price if not found
            
            # Calculate performance metrics
            total_cost = shares * avg_price
            current_value = shares * current_price
            gain_loss = current_value - total_cost
            gain_loss_percent = (gain_loss / total_cost * 100) if total_cost > 0 else 0
            
            formatted_item = {
                'symbol': symbol,
                'company_name': item['company_name'],
                'shares': shares,
                'cost_basis': avg_price,
                'price': current_price,
                'total_cost': total_cost,
                'current_value': current_value,
                'gain_loss': gain_loss,
                'gain_loss_percent': gain_loss_percent,
                'updated_at': item.get('updated_at', '').isoformat() if item.get('updated_at') else None
            }
            formatted_portfolio.append(formatted_item)
        
        return JsonResponse(formatted_portfolio, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_portfolio_metrics(request):
    """
    API endpoint to get overall portfolio performance metrics
    
    Query parameters:
        timeframe (optional): Time period for performance calculation (1D, 1W, 1M, 3M, 6M, 1Y, ALL)
    
    Returns:
        JSON response containing portfolio metrics like total value, gains, top performers
    """
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Get timeframe parameter
        timeframe = request.GET.get('timeframe', '1M')
        
        portfolio_repo = PortfolioRepository()
        stock_service = StockMarketService()
        
        # Get user's portfolio
        portfolio_items = portfolio_repo.get_user_portfolio(user_id)
        
        if not portfolio_items:
            return JsonResponse({
                'total_value': 0,
                'total_cost': 0,
                'total_gain_loss': 0,
                'total_gain_loss_percent': 0,
                'total_stocks': 0,
                'top_performer': None,
                'worst_performer': None,
                'portfolio_distribution': []
            })
        
        # Get current market prices
        market_data = stock_service.get_symbol_and_price(source='VCI')
        price_map = {item['symbol']: item.get('price', 0) for item in market_data}
        
        # Calculate overall metrics
        total_value = 0
        total_cost = 0
        portfolio_distribution = []
        performances = []
        
        for item in portfolio_items:
            symbol = item['symbol']
            shares = float(item['shares'])
            avg_price = float(item['avg_price'])
            current_price = price_map.get(symbol, avg_price)
            
            item_cost = shares * avg_price
            item_value = shares * current_price
            item_gain_loss_percent = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
            
            total_cost += item_cost
            total_value += item_value
            
            performances.append({
                'symbol': symbol,
                'company_name': item['company_name'],
                'gain_loss_percent': item_gain_loss_percent,
                'value': item_value
            })
        
        # Calculate total metrics
        total_gain_loss = total_value - total_cost
        total_gain_loss_percent = (total_gain_loss / total_cost * 100) if total_cost > 0 else 0
        
        # Find top and worst performers
        performances.sort(key=lambda x: x['gain_loss_percent'], reverse=True)
        top_performer = performances[0] if performances else None
        worst_performer = performances[-1] if performances else None
        
        # Calculate portfolio distribution
        for perf in performances:
            allocation = (perf['value'] / total_value * 100) if total_value > 0 else 0
            portfolio_distribution.append({
                'symbol': perf['symbol'],
                'company_name': perf['company_name'],
                'allocation': allocation,
                'value': perf['value']
            })
        
        return JsonResponse({
            'total_value': total_value,
            'total_cost': total_cost,
            'total_gain_loss': total_gain_loss,
            'total_gain_loss_percent': total_gain_loss_percent,
            'total_stocks': len(portfolio_items),
            'top_performer': top_performer,
            'worst_performer': worst_performer,
            'portfolio_distribution': portfolio_distribution,
            'timeframe': timeframe
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============== PRICE ALERTS ENDPOINTS ==============

@csrf_exempt
@require_http_methods(["GET"])
def get_user_alerts(request):
    """
    API endpoint to get all price alerts for the authenticated user
    
    Returns:
        JSON response containing list of user's price alerts
    """
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        alerts_repo = AlertsRepository()
        stock_service = StockMarketService()
        
        # Get user alerts
        alerts = alerts_repo.get_user_alerts(user_id)
        
        if not alerts:
            return JsonResponse([], safe=False)
        
        # Get current prices for all symbols in alerts
        symbols = list(set([alert['symbol'] for alert in alerts]))
        try:
            market_data = stock_service.get_symbol_and_price(source='VCI')
            price_map = {item['symbol']: item.get('price', 0) for item in market_data}
        except Exception:
            price_map = {}
        
        # Format alerts with current prices
        formatted_alerts = []
        for alert in alerts:
            current_price = price_map.get(alert['symbol'], 0)
            
            # Check if alert should be triggered
            should_trigger = False
            if alert['is_active'] and not alert['triggered']:
                if alert['alert_type'] == 'price_above' and current_price >= float(alert['target_price']):
                    should_trigger = True
                elif alert['alert_type'] == 'price_below' and current_price <= float(alert['target_price']):
                    should_trigger = True
            
            # Update triggered status if needed
            if should_trigger:
                alerts_repo.update_triggered_alerts(alert['symbol'], Decimal(str(current_price)))
                alert['triggered'] = True
            
            formatted_alert = {
                'id': alert['id'],
                'symbol': alert['symbol'],
                'companyName': alert['company_name'],
                'alertType': alert['alert_type'],
                'targetPrice': float(alert['target_price']),
                'currentPrice': current_price,
                'isActive': bool(alert['is_active']),
                'notes': alert['notes'] or '',
                'triggered': bool(alert['triggered']),
                'createdAt': alert['created_at'].strftime('%Y-%m-%d') if alert['created_at'] else None
            }
            formatted_alerts.append(formatted_alert)
        
        return JsonResponse(formatted_alerts, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_alert(request):
    """
    API endpoint to create a new price alert
    
    Expected JSON payload:
    {
        "symbol": "AAPL",
        "companyName": "Apple Inc.",
        "alertType": "price_above",
        "targetPrice": 180.00,
        "isActive": true,
        "notes": "Optional notes"
    }
    
    Returns:
        JSON response with success/error message
    """
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['symbol', 'companyName', 'alertType', 'targetPrice']
        for field in required_fields:
            if field not in data or not data[field]:
                return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
        
        # Validate alert type
        if data['alertType'] not in ['price_above', 'price_below']:
            return JsonResponse({'error': 'Invalid alert type'}, status=400)
        
        # Validate target price
        try:
            target_price = Decimal(str(data['targetPrice']))
            if target_price <= 0:
                return JsonResponse({'error': 'Target price must be positive'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid target price'}, status=400)
        
        alerts_repo = AlertsRepository()
        
        success = alerts_repo.create_alert(
            user_id=user_id,
            symbol=data['symbol'].upper(),
            company_name=data['companyName'],
            alert_type=data['alertType'],
            target_price=target_price,
            is_active=data.get('isActive', True),
            notes=data.get('notes', '')
        )
        
        if success:
            return JsonResponse({'message': 'Alert created successfully'})
        else:
            return JsonResponse({'error': 'Failed to create alert'}, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT"])
def update_alert(request, alert_id):
    """
    API endpoint to update an existing price alert
    
    URL: /portfolio/alerts/<alert_id>/
    
    Expected JSON payload:
    {
        "symbol": "AAPL",
        "companyName": "Apple Inc.",
        "alertType": "price_above",
        "targetPrice": 180.00,
        "isActive": true,
        "notes": "Updated notes"
    }
    
    Returns:
        JSON response with success/error message
    """
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['symbol', 'companyName', 'alertType', 'targetPrice']
        for field in required_fields:
            if field not in data or not data[field]:
                return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
        
        # Validate alert type
        if data['alertType'] not in ['price_above', 'price_below']:
            return JsonResponse({'error': 'Invalid alert type'}, status=400)
        
        # Validate target price
        try:
            target_price = Decimal(str(data['targetPrice']))
            if target_price <= 0:
                return JsonResponse({'error': 'Target price must be positive'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid target price'}, status=400)
        
        alerts_repo = AlertsRepository()
        
        # Check if alert exists and belongs to user
        existing_alert = alerts_repo.get_alert_by_id(int(alert_id), user_id)
        if not existing_alert:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        
        success = alerts_repo.update_alert(
            alert_id=int(alert_id),
            user_id=user_id,
            symbol=data['symbol'].upper(),
            company_name=data['companyName'],
            alert_type=data['alertType'],
            target_price=target_price,
            is_active=data.get('isActive', True),
            notes=data.get('notes', '')
        )
        
        if success:
            return JsonResponse({'message': 'Alert updated successfully'})
        else:
            return JsonResponse({'error': 'Failed to update alert'}, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'Invalid alert ID'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_prospective_stocks(request):
    """
    API endpoint to get prospective stocks based on fundamental analysis criteria.

    Criteria for prospective stocks:
    - Favorable P/E ratio (< 25)
    - Positive 2-year EPS growth
    - Positive 2-year net profit growth
    - Recent positive news/developments

    Returns:
        JSON response containing list of prospective stocks with fundamental metrics
    """
    try:
        # Initialize services
        stock_service = StockMarketService()

        # Get market data
        try:
            market_data = stock_service.get_symbol_and_price(source='VCI')
            price_map = {item['symbol']: item.get('price', 0) for item in market_data}
        except Exception:
            price_map = {}

        # Curated list of prospective stocks based on fundamental analysis
        # In a production environment, this would come from a database or real-time analysis
        prospective_stocks = [
            {
                'symbol': 'FPT',
                'name': 'FPT Corporation',
                'price': price_map.get('FPT', 125.50),
                'peRatio': 18.5,
                'epsGrowth2Y': 22.4,
                'netProfitGrowth2Y': 25.8,
                'news': 'Signed major AI partnership with NVIDIA, expanding digital transformation services globally.',
                'sector': 'Technology'
            },
            {
                'symbol': 'MWG',
                'name': 'Mobile World Investment Corporation',
                'price': price_map.get('MWG', 52.80),
                'peRatio': 14.2,
                'epsGrowth2Y': 18.6,
                'netProfitGrowth2Y': 20.3,
                'news': 'Strong retail expansion with new store openings and e-commerce growth accelerating.',
                'sector': 'Retail'
            },
            {
                'symbol': 'VHM',
                'name': 'Vinhomes JSC',
                'price': price_map.get('VHM', 42.30),
                'peRatio': 8.9,
                'epsGrowth2Y': 15.2,
                'netProfitGrowth2Y': 17.8,
                'news': 'New township projects launching with strong pre-sales demand.',
                'sector': 'Real Estate'
            },
            {
                'symbol': 'HPG',
                'name': 'Hoa Phat Group JSC',
                'price': price_map.get('HPG', 28.50),
                'peRatio': 10.5,
                'epsGrowth2Y': 12.8,
                'netProfitGrowth2Y': 14.5,
                'news': 'Steel demand recovering with infrastructure projects and export growth.',
                'sector': 'Steel'
            },
            {
                'symbol': 'VNM',
                'name': 'Vietnam Dairy Products JSC',
                'price': price_map.get('VNM', 72.00),
                'peRatio': 16.8,
                'epsGrowth2Y': 8.5,
                'netProfitGrowth2Y': 10.2,
                'news': 'Expanding into plant-based products and premium dairy segments.',
                'sector': 'Consumer Goods'
            },
            {
                'symbol': 'ACB',
                'name': 'Asia Commercial Bank',
                'price': price_map.get('ACB', 24.80),
                'peRatio': 7.2,
                'epsGrowth2Y': 16.4,
                'netProfitGrowth2Y': 18.9,
                'news': 'Digital banking transformation driving customer acquisition and efficiency.',
                'sector': 'Banking'
            }
        ]

        return JsonResponse(prospective_stocks, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_alert(request, alert_id):
    """
    API endpoint to delete a price alert
    
    URL: /portfolio/alerts/<alert_id>/
    
    Returns:
        JSON response with success/error message
    """
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        alerts_repo = AlertsRepository()
        
        # Check if alert exists and belongs to user
        existing_alert = alerts_repo.get_alert_by_id(int(alert_id), user_id)
        if not existing_alert:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        
        success = alerts_repo.delete_alert(int(alert_id), user_id)
        
        if success:
            return JsonResponse({'message': 'Alert deleted successfully'})
        else:
            return JsonResponse({'error': 'Failed to delete alert'}, status=500)
    
    except ValueError:
        return JsonResponse({'error': 'Invalid alert ID'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def toggle_alert(request, alert_id):
    """
    API endpoint to toggle the active status of a price alert

    URL: /portfolio/alerts/<alert_id>/toggle/

    Returns:
        JSON response with success/error message
    """
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        alerts_repo = AlertsRepository()

        # Check if alert exists and belongs to user
        existing_alert = alerts_repo.get_alert_by_id(int(alert_id), user_id)
        if not existing_alert:
            return JsonResponse({'error': 'Alert not found'}, status=404)

        success = alerts_repo.toggle_alert_status(int(alert_id), user_id)

        if success:
            new_status = 'activated' if not existing_alert['is_active'] else 'deactivated'
            return JsonResponse({'message': f'Alert {new_status} successfully'})
        else:
            return JsonResponse({'error': 'Failed to toggle alert status'}, status=500)

    except ValueError:
        return JsonResponse({'error': 'Invalid alert ID'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============== STOCK DATA SYNC ENDPOINTS ==============

@csrf_exempt
@require_http_methods(["GET"])
def get_sync_status(request):
    """
    API endpoint to get sync status for stocks in user's portfolio.

    Returns:
        JSON response containing sync status for each portfolio stock
    """
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        portfolio_repo = PortfolioRepository()
        sync_service = StockDataSyncService()

        # Get user's portfolio symbols
        symbols = portfolio_repo.get_user_portfolio_symbols(user_id)

        if not symbols:
            return JsonResponse([], safe=False)

        # Get sync status for each symbol
        statuses = []
        for symbol in symbols:
            status = sync_service.get_sync_status(symbol)
            statuses.append({
                'symbol': symbol,
                'status': status.get('sync_status', 'not_synced') if status else 'not_synced',
                'last_sync': status.get('last_sync_date').isoformat() if status and status.get('last_sync_date') else None,
                'total_records': status.get('total_records', 0) if status else 0,
                'earliest_date': str(status.get('earliest_data_date', ''))[:10] if status and status.get('earliest_data_date') else None,
                'latest_date': str(status.get('latest_data_date', ''))[:10] if status and status.get('latest_data_date') else None
            })

        return JsonResponse(statuses, safe=False)
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def trigger_sync(request, symbol):
    """
    API endpoint to manually trigger data sync for a specific symbol.

    URL: /portfolio/sync/<symbol>/

    Returns:
        JSON response with sync result
    """
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        symbol = symbol.upper()

        # Verify symbol is in user's portfolio
        portfolio_repo = PortfolioRepository()
        portfolio_symbols = portfolio_repo.get_user_portfolio_symbols(user_id)

        if symbol not in portfolio_symbols:
            return JsonResponse({'error': 'Stock not in portfolio'}, status=400)

        # Trigger sync
        sync_service = StockDataSyncService()

        # Check if force_full was requested
        try:
            data = json.loads(request.body) if request.body else {}
            force_full = data.get('force_full', False)
        except json.JSONDecodeError:
            force_full = False

        sync_result = sync_service.sync_stock_data(symbol, force_full=force_full)

        return JsonResponse({
            'symbol': symbol,
            'status': sync_result.status,
            'records_added': sync_result.records_added,
            'message': sync_result.message,
            'earliest_date': sync_result.earliest_date,
            'latest_date': sync_result.latest_date
        })
    except Exception as e:
        logger.error(f"Error triggering sync for {symbol}: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_portfolio_with_sync(request):
    """
    API endpoint to get portfolio items with their sync status.

    Returns:
        JSON response containing portfolio items with sync information
    """
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        portfolio_repo = PortfolioRepository()
        portfolio_items = portfolio_repo.get_portfolio_with_sync_status(user_id)

        formatted_portfolio = []
        for item in portfolio_items:
            formatted_item = {
                'symbol': item['symbol'],
                'name': item['company_name'],
                'shares': float(item['shares']),
                'avgPrice': float(item['avg_price']),
                'sync_status': item.get('sync_status', 'not_synced'),
                'last_sync': item.get('last_sync_date').isoformat() if item.get('last_sync_date') else None,
                'total_records': item.get('total_records', 0),
                'data_coverage': {
                    'earliest': str(item.get('earliest_data_date', ''))[:10] if item.get('earliest_data_date') else None,
                    'latest': str(item.get('latest_data_date', ''))[:10] if item.get('latest_data_date') else None
                }
            }
            formatted_portfolio.append(formatted_item)

        return JsonResponse(formatted_portfolio, safe=False)
    except Exception as e:
        logger.error(f"Error getting portfolio with sync: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
