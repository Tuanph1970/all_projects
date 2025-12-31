from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import jwt
from repositories.portfolio_repository import PortfolioRepository
from services.stock_entities import StockService
import logging

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
def get_recommendations(request):
    """
    Generate stock recommendations based on user's portfolio
    Only recommends stocks that the user currently owns
    Uses real market data and technical analysis
    
    Returns:
        JSON response containing list of recommendations with:
        - type: BUY, SELL, or HOLD
        - symbol: Stock symbol
        - name: Company name
        - reason: Analysis-based reasoning
        - confidence: Confidence percentage (0-100)
    """
    try:
        user_id = get_user_id_from_token(request)
        if not user_id:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        portfolio_repo = PortfolioRepository()
        portfolio_items = portfolio_repo.get_user_portfolio(user_id)
        
        if not portfolio_items:
            return JsonResponse([], safe=False)
        
        # Initialize stock service
        stock_service = StockService(symbol="VIC", source="VCI")
        recommendations = []
        
        for portfolio_item in portfolio_items:
            symbol = portfolio_item['symbol']
            company_name = portfolio_item['company_name']
            
            try:
                # Get technical indicators and analysis
                recommendation = analyze_stock_for_recommendation(
                    stock_service, symbol, company_name
                )
                
                if recommendation:
                    recommendations.append(recommendation)
                    
            except Exception as e:
                logger.warning(f"Failed to analyze {symbol}: {e}")
                continue
        
        # Sort by confidence score
        recommendations.sort(key=lambda x: x['confidence'], reverse=True)
        
        return JsonResponse(recommendations, safe=False)
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return JsonResponse({'error': 'Failed to generate recommendations'}, status=500)


def analyze_stock_for_recommendation(stock_service: StockService, symbol: str, company_name: str) -> dict:
    """
    Analyze individual stock and generate recommendation
    
    Args:
        stock_service: Instance of StockService
        symbol: Stock symbol
        company_name: Company name
    
    Returns:
        Dictionary with recommendation details
    """
    try:
        # Get technical indicators
        indicators = stock_service.get_technical_indicators(symbol)
        
        if not indicators:
            return None
            
        current_price = indicators.get('current_price', 0)
        rsi = indicators.get('rsi', 50)
        sma_20 = indicators.get('sma_20', current_price)
        sma_50 = indicators.get('sma_50', current_price)
        sma_200 = indicators.get('sma_200', current_price)
        high_52w = indicators.get('high_52w', current_price)
        low_52w = indicators.get('low_52w', current_price)
        
        # Get price history for trend analysis
        price_history = stock_service.get_price_history(
            symbol=symbol,
            start='2024-01-01',
            end=None
        )
        
        # Calculate recommendation based on technical analysis
        recommendation_type, reason, confidence = generate_recommendation_logic(
            current_price, rsi, sma_20, sma_50, sma_200, 
            high_52w, low_52w, price_history, symbol
        )
        
        return {
            'type': recommendation_type,
            'symbol': symbol,
            'name': company_name,
            'reason': reason,
            'confidence': confidence
        }
        
    except Exception as e:
        logger.error(f"Error analyzing stock {symbol}: {e}")
        return None


def generate_recommendation_logic(current_price, rsi, sma_20, sma_50, sma_200, 
                                high_52w, low_52w, price_history, symbol):
    """
    Generate recommendation based on technical indicators
    
    Returns:
        tuple: (recommendation_type, reason, confidence)
    """
    reasons = []
    buy_signals = 0
    sell_signals = 0
    confidence_factors = []
    
    # RSI Analysis
    if rsi < 30:
        buy_signals += 2
        reasons.append("RSI indicates oversold conditions")
        confidence_factors.append(15)
    elif rsi > 70:
        sell_signals += 2
        reasons.append("RSI shows overbought conditions")
        confidence_factors.append(15)
    
    # Moving Average Analysis
    if current_price > sma_20 and sma_20 > sma_50 and sma_50 > sma_200:
        buy_signals += 3
        reasons.append("Strong upward trend across all moving averages")
        confidence_factors.append(25)
    elif current_price < sma_20 and sma_20 < sma_50 and sma_50 < sma_200:
        sell_signals += 3
        reasons.append("Bearish trend across moving averages")
        confidence_factors.append(25)
    elif current_price > sma_20 > sma_50:
        buy_signals += 1
        reasons.append("Price above short-term moving averages")
        confidence_factors.append(10)
    elif current_price < sma_20 < sma_50:
        sell_signals += 1
        reasons.append("Price below short-term moving averages")
        confidence_factors.append(10)
    
    # 52-week high/low analysis
    price_position = (current_price - low_52w) / (high_52w - low_52w) if high_52w > low_52w else 0.5
    
    if price_position < 0.2:
        buy_signals += 1
        reasons.append(f"Trading near 52-week low, potential value opportunity")
        confidence_factors.append(10)
    elif price_position > 0.9:
        sell_signals += 1
        reasons.append(f"Trading near 52-week high, consider profit taking")
        confidence_factors.append(10)
    
    # Volume and momentum analysis (if price history available)
    if not price_history.empty and len(price_history) > 5:
        recent_trend = price_history['close'].tail(5).pct_change().mean()
        if recent_trend > 0.02:  # 2% average daily gain
            buy_signals += 1
            reasons.append("Strong recent momentum")
            confidence_factors.append(8)
        elif recent_trend < -0.02:  # 2% average daily loss
            sell_signals += 1
            reasons.append("Weak recent momentum")
            confidence_factors.append(8)
    
    # Determine recommendation
    total_signals = buy_signals + sell_signals
    
    if buy_signals > sell_signals and buy_signals >= 2:
        recommendation_type = "BUY"
        base_confidence = min(70 + (buy_signals * 5), 95)
    elif sell_signals > buy_signals and sell_signals >= 2:
        recommendation_type = "SELL"
        base_confidence = min(65 + (sell_signals * 5), 90)
    else:
        recommendation_type = "HOLD"
        base_confidence = 60
        reasons.append("Mixed signals suggest maintaining current position")
    
    # Calculate final confidence
    confidence_boost = sum(confidence_factors[:3])  # Cap at top 3 factors
    final_confidence = min(base_confidence + confidence_boost, 98)
    
    # Format reason
    if len(reasons) > 3:
        reason = ". ".join(reasons[:3]) + f" and {len(reasons) - 3} other factors"
    else:
        reason = ". ".join(reasons) if reasons else f"Technical analysis suggests {recommendation_type.lower()} signal"
    
    return recommendation_type, reason, int(final_confidence)