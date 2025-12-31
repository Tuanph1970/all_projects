from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from django.http import HttpResponse
from services.stock_entity_service import MarketStockEntity
from services.stock_entities import StockService
from core.exceptions import ExternalServiceException, ValidationException
import pandas as pd
import numpy as np
import logging
import json

logger = logging.getLogger(__name__)


class NanInfEncoder(json.JSONEncoder):
    """Custom JSON encoder that converts NaN and Inf to null"""
    def iterencode(self, obj, _one_shot=False):
        """Encode object, converting NaN and Inf to null"""
        for chunk in super().iterencode(obj, _one_shot):
            # Replace JavaScript NaN and Infinity with null in the output
            chunk = chunk.replace('NaN', 'null')
            chunk = chunk.replace('Infinity', 'null')
            chunk = chunk.replace('-Infinity', 'null')
            yield chunk


def clean_dict_values(d):
    """Clean dictionary values for JSON serialization"""
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
            cleaned[k] = [clean_dict_values(item) if isinstance(item, dict) else item for item in v]
        else:
            cleaned[k] = v
    return cleaned


@api_view(['GET'])
def get_all_industries(request):
    """
    Get list of all available industries
    """
    try:
        stock_service = StockService()
        industries = stock_service.get_industries()

        if industries.empty:
            return Response({
                'success': True,
                'data': [],
                'total': 0
            })

        # Convert to JSON format and clean NaN values
        result = [clean_dict_values(row) for row in industries.to_dict('records')]

        # Use custom JSON encoder
        response_data = {
            'success': True,
            'data': result,
            'total': len(result)
        }
        json_data = json.dumps(response_data, cls=NanInfEncoder)
        return HttpResponse(json_data, content_type='application/json')

    except Exception as e:
        logger.error(f"Error getting industries: {e}")
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_stocks_by_industry_code(request, industry_code):
    """
    Get stocks filtered by industry code
    """
    try:
        # Get query parameters for pagination and filtering
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 50))
        sort_by = request.GET.get('sort_by', 'symbol')
        sort_order = request.GET.get('sort_order', 'asc')
        include_analysis = request.GET.get('include_analysis', 'false').lower() == 'true'

        stock_service = StockService()
        stocks = stock_service.get_stocks_by_industry(industry_code)

        if stocks.empty:
            return Response({
                'success': True,
                'data': [],
                'total': 0,
                'industry_code': industry_code,
                'page': page,
                'per_page': per_page
            })

        # Apply sorting
        if sort_by in stocks.columns:
            ascending = sort_order.lower() == 'asc'
            stocks = stocks.sort_values(by=sort_by, ascending=ascending)

        # Calculate pagination
        total_records = len(stocks)
        total_pages = (total_records + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        # Get paginated data
        paginated_stocks = stocks.iloc[start_idx:end_idx]

        result = []
        for _, stock in paginated_stocks.iterrows():
            stock_data = stock.to_dict()

            # Add basic analysis if requested
            if include_analysis and 'symbol' in stock_data:
                try:
                    # Get additional analysis data
                    analysis = stock_service.analyze_stock(stock_data['symbol'])
                    if not analysis.empty:
                        analysis_data = analysis.iloc[0].to_dict()
                        stock_data.update(analysis_data)
                except Exception as e:
                    logger.warning(f"Failed to get analysis for {stock_data.get('symbol', 'N/A')}: {e}")

            # Clean NaN/Infinity values
            cleaned_stock = clean_dict_values(stock_data)
            result.append(cleaned_stock)

        # Use custom JSON encoder
        response_data = {
            'success': True,
            'data': result,
            'total': total_records,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'industry_code': industry_code,
            'include_analysis': include_analysis
        }
        json_data = json.dumps(response_data, cls=NanInfEncoder)
        return HttpResponse(json_data, content_type='application/json')

    except ValueError as e:
        return Response({
            'error': f'Invalid parameter: {e}',
            'success': False
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error getting stocks by industry {industry_code}: {e}")
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_industry_analysis(request, industry_code):
    """
    Get comprehensive analysis of an industry
    """
    try:
        stock_service = StockService()

        # Get all stocks in the industry
        stocks = stock_service.get_stocks_by_industry(industry_code)

        if stocks.empty:
            return Response({
                'success': True,
                'data': {
                    'industry_code': industry_code,
                    'total_stocks': 0,
                    'analysis': {}
                }
            })

        # Perform industry analysis
        symbols = stocks['symbol'].tolist() if 'symbol' in stocks.columns else []

        if symbols:
            # Analyze top stocks in the industry (limit to 20 for performance)
            top_symbols = symbols[:20]
            industry_analysis = stock_service.analyze_stock(top_symbols)

            # Calculate industry metrics
            analysis_summary = {}
            if not industry_analysis.empty:
                analysis_summary = {
                    'average_pe': industry_analysis['P/E'].mean() if 'P/E' in industry_analysis.columns else None,
                    'average_pb': industry_analysis['P/B'].mean() if 'P/B' in industry_analysis.columns else None,
                    'average_roe': industry_analysis['ROE'].mean() if 'ROE' in industry_analysis.columns else None,
                    'average_roa': industry_analysis['ROA'].mean() if 'ROA' in industry_analysis.columns else None,
                    'average_market_cap': industry_analysis['MarketCap'].mean() if 'MarketCap' in industry_analysis.columns else None,
                    'total_market_cap': industry_analysis['MarketCap'].sum() if 'MarketCap' in industry_analysis.columns else None,
                    'price_change_stats': {
                        'average_change': industry_analysis['Change%'].mean() if 'Change%' in industry_analysis.columns else None,
                        'positive_movers': len(industry_analysis[industry_analysis['Change%'] > 0]) if 'Change%' in industry_analysis.columns else 0,
                        'negative_movers': len(industry_analysis[industry_analysis['Change%'] < 0]) if 'Change%' in industry_analysis.columns else 0
                    }
                }

            # Get top performers
            top_performers = []
            if not industry_analysis.empty and 'Change%' in industry_analysis.columns:
                top_performers = industry_analysis.nlargest(5, 'Change%')[['Symbol', 'Company', 'Change%', 'Price']].to_dict('records')

            # Get industry information
            industries = stock_service.get_industries()
            industry_info = {}
            if not industries.empty:
                industry_match = industries[industries['code'] == industry_code] if 'code' in industries.columns else pd.DataFrame()
                if not industry_match.empty:
                    industry_info = industry_match.iloc[0].to_dict()

            result = {
                'industry_code': industry_code,
                'industry_info': industry_info,
                'total_stocks': len(stocks),
                'analyzed_stocks': len(industry_analysis) if not industry_analysis.empty else 0,
                'analysis_summary': analysis_summary,
                'top_performers': top_performers,
                'stocks_sample': [clean_dict_values(s) for s in stocks.head(10).to_dict('records')]
            }

        else:
            result = {
                'industry_code': industry_code,
                'total_stocks': len(stocks),
                'analysis': {},
                'message': 'No symbols found for analysis'
            }

        # Clean and encode
        cleaned_result = clean_dict_values(result)
        response_data = {
            'success': True,
            'data': cleaned_result
        }
        json_data = json.dumps(response_data, cls=NanInfEncoder)
        return HttpResponse(json_data, content_type='application/json')

    except Exception as e:
        logger.error(f"Error getting industry analysis for {industry_code}: {e}")
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def compare_industries(request):
    """
    Compare multiple industries
    """
    try:
        data = JSONParser().parse(request)
        industry_codes = data.get('industry_codes', [])

        if not industry_codes:
            return Response({
                'error': 'No industry codes provided',
                'success': False
            }, status=status.HTTP_400_BAD_REQUEST)

        stock_service = StockService()
        comparison_data = []

        for industry_code in industry_codes:
            try:
                # Get stocks in this industry
                stocks = stock_service.get_stocks_by_industry(industry_code)

                if not stocks.empty:
                    symbols = stocks['symbol'].tolist()[:10]  # Limit for performance

                    if symbols:
                        analysis = stock_service.analyze_stock(symbols)

                        industry_stats = {
                            'industry_code': industry_code,
                            'total_stocks': len(stocks),
                            'analyzed_stocks': len(analysis) if not analysis.empty else 0
                        }

                        if not analysis.empty:
                            industry_stats.update({
                                'average_pe': analysis['P/E'].mean() if 'P/E' in analysis.columns else None,
                                'average_pb': analysis['P/B'].mean() if 'P/B' in analysis.columns else None,
                                'average_roe': analysis['ROE'].mean() if 'ROE' in analysis.columns else None,
                                'average_market_cap': analysis['MarketCap'].mean() if 'MarketCap' in analysis.columns else None,
                                'average_change': analysis['Change%'].mean() if 'Change%' in analysis.columns else None
                            })

                        comparison_data.append(industry_stats)
                    else:
                        comparison_data.append({
                            'industry_code': industry_code,
                            'total_stocks': len(stocks),
                            'error': 'No symbols available for analysis'
                        })
                else:
                    comparison_data.append({
                        'industry_code': industry_code,
                        'total_stocks': 0,
                        'error': 'No stocks found in this industry'
                    })

            except Exception as e:
                logger.warning(f"Error analyzing industry {industry_code}: {e}")
                comparison_data.append({
                    'industry_code': industry_code,
                    'error': str(e)
                })

        return Response({
            'success': True,
            'data': comparison_data,
            'total_industries': len(comparison_data)
        })

    except Exception as e:
        logger.error(f"Error comparing industries: {e}")
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_industry_performance(request, industry_code):
    """
    Get industry performance metrics over time
    """
    try:
        period = request.GET.get('period', '1M')  # 1D, 1W, 1M, 3M, 6M, 1Y
        limit = int(request.GET.get('limit', 10))

        stock_service = StockService()

        # Get stocks in the industry
        stocks = stock_service.get_stocks_by_industry(industry_code)

        if stocks.empty:
            return Response({
                'success': True,
                'data': {
                    'industry_code': industry_code,
                    'performance': {},
                    'message': 'No stocks found in this industry'
                }
            })

        # Get top stocks by market cap or volume for performance calculation
        symbols = stocks['symbol'].tolist()[:limit] if 'symbol' in stocks.columns else []

        performance_data = []
        if symbols:
            for symbol in symbols:
                try:
                    # Get recent price history for each stock
                    price_data = stock_service.get_price_history(
                        symbol=symbol,
                        start='2024-01-01',
                        end='2024-12-31'
                    )

                    if not price_data.empty:
                        latest_price = price_data.iloc[-1]
                        first_price = price_data.iloc[0]

                        performance = {
                            'symbol': symbol,
                            'current_price': latest_price.get('close', 0),
                            'period_return': ((latest_price.get('close', 0) / first_price.get('close', 1)) - 1) * 100 if first_price.get('close', 0) > 0 else 0,
                            'volume': latest_price.get('volume', 0)
                        }
                        performance_data.append(performance)

                except Exception as e:
                    logger.warning(f"Error getting performance for {symbol}: {e}")

        # Calculate industry aggregate performance
        aggregate_performance = {}
        if performance_data:
            returns = [stock['period_return'] for stock in performance_data]
            aggregate_performance = {
                'average_return': sum(returns) / len(returns),
                'best_performer': max(performance_data, key=lambda x: x['period_return']),
                'worst_performer': min(performance_data, key=lambda x: x['period_return']),
                'total_stocks_analyzed': len(performance_data)
            }

        result = {
            'industry_code': industry_code,
            'period': period,
            'individual_performance': performance_data,
            'aggregate_performance': aggregate_performance
        }

        return Response({
            'success': True,
            'data': result
        })

    except Exception as e:
        logger.error(f"Error getting industry performance for {industry_code}: {e}")
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)