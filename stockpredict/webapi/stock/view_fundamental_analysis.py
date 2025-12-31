"""
Fundamental Analysis API Views
Provides comprehensive fundamental analysis data for stocks including
financial statements, ratios, company profile, and valuation metrics.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
import logging
from datetime import datetime, timedelta
from services.stock_entities import StockService, DataSource, Period

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['GET'])
def get_fundamental_analysis(request, symbol):
    """
    Get comprehensive fundamental analysis data for a stock symbol
    
    Args:
        symbol: Stock ticker symbol (e.g., 'VIC', 'VNM')
    
    Returns:
        JSON response with fundamental analysis data
    """
    try:
        # Initialize stock service
        service = StockService(symbol=symbol, source=DataSource.VCI.value)
        
        # Prepare the response data
        analysis_data = {}
        
        # 1. Company Overview and Profile
        try:
            company_overview = service.get_company_overview(symbol)
            company_profile = service.get_company_profile(symbol)
            
            analysis_data['company_info'] = {
                'name': company_overview.get('symbol', symbol),  # Use symbol as name fallback
                'symbol': symbol,
                'exchange': company_overview.get('exchange', 'HOSE'),  # Default to HOSE for TCB
                'industry': company_overview.get('icb_name3', company_overview.get('icb_name2', '')),
                'sector': company_overview.get('icb_name2', ''),
                'marketCap': company_overview.get('charter_capital', 0),
                'employees': company_profile.get('employees', 0),
                'website': company_profile.get('website', ''),
                'description': company_overview.get('company_profile', company_profile.get('description', '')),
                'founded': company_profile.get('founded', ''),
                'headquarters': company_profile.get('headquarters', '')
            }
        except Exception as e:
            logger.warning(f"Error getting company info for {symbol}: {e}")
            analysis_data['company_info'] = {}
        
        # 2. Financial Statements
        try:
            # Get latest financial statements (yearly)
            income_statement = service.get_income_statement(symbol, period=Period.YEAR.value)
            balance_sheet = service.get_balance_sheet(symbol, period=Period.YEAR.value)
            cash_flow = service.get_cash_flow(symbol, period=Period.YEAR.value)
            
            # Process income statement
            if not income_statement.empty:
                latest_income = income_statement.iloc[-1].to_dict() if len(income_statement) > 0 else {}
                analysis_data['income_statement'] = {
                    'revenue': latest_income.get('Revenue (Bn. VND)', latest_income.get('Total operating revenue', 0)),
                    'grossProfit': latest_income.get('Gross Profit', latest_income.get('Operating Profit before Provision', 0)),
                    'operatingIncome': latest_income.get('Operating Income', latest_income.get('Operating Profit before Provision', 0)),
                    'netIncome': latest_income.get('Net Income', latest_income.get('Net Profit For the Year', latest_income.get('Attributable to parent company', 0))),
                    'eps': latest_income.get('EPS', latest_income.get('EPS_basis', 0)),
                    'ebitda': latest_income.get('EBITDA', latest_income.get('Profit before tax', 0))
                }
            else:
                analysis_data['income_statement'] = {}
                
            # Process balance sheet
            if not balance_sheet.empty:
                latest_balance = balance_sheet.iloc[-1].to_dict() if len(balance_sheet) > 0 else {}
                analysis_data['balance_sheet'] = {
                    'totalAssets': latest_balance.get('TOTAL ASSETS (Bn. VND)', latest_balance.get('Total Assets', 0)),
                    'totalLiabilities': latest_balance.get('LIABILITIES (Bn. VND)', latest_balance.get('Total Liabilities', 0)),
                    'totalEquity': latest_balance.get("OWNER'S EQUITY(Bn.VND)", latest_balance.get('Total Equity', 0)),
                    'currentAssets': latest_balance.get('Current Assets', latest_balance.get('Cash and cash equivalents (Bn. VND)', 0)),
                    'currentLiabilities': latest_balance.get('Current Liabilities', latest_balance.get('Deposits from customers', 0)),
                    'longTermDebt': latest_balance.get('Long Term Debt', latest_balance.get('Convertible bonds/CDs and other valuable papers issued', 0)),
                    'cash': latest_balance.get('Cash', latest_balance.get('Cash and cash equivalents (Bn. VND)', 0))
                }
            else:
                analysis_data['balance_sheet'] = {}
                
            # Process cash flow
            if not cash_flow.empty:
                latest_cash = cash_flow.iloc[-1].to_dict() if len(cash_flow) > 0 else {}
                analysis_data['cash_flow'] = {
                    'operatingCashFlow': latest_cash.get('Operating Cash Flow', 0),
                    'investingCashFlow': latest_cash.get('Investing Cash Flow', 0),
                    'financingCashFlow': latest_cash.get('Financing Cash Flow', 0),
                    'freeCashFlow': latest_cash.get('Free Cash Flow', 0),
                    'netCashFlow': latest_cash.get('Net Cash Flow', 0)
                }
            else:
                analysis_data['cash_flow'] = {}
                
        except Exception as e:
            logger.warning(f"Error getting financial statements for {symbol}: {e}")
            analysis_data['income_statement'] = {}
            analysis_data['balance_sheet'] = {}
            analysis_data['cash_flow'] = {}
        
        # 3. Financial Ratios
        try:
            ratios = service.get_financial_ratios(symbol, period=Period.YEAR.value)
            
            if not ratios.empty:
                latest_ratios = ratios.iloc[-1].to_dict() if len(ratios) > 0 else {}

                # Handle multi-level column names (tuples) from vnstock
                # Extract values by looking for the correct tuple keys
                pe_value = 0
                pb_value = 0
                ps_value = 0
                roe_value = 0
                roa_value = 0
                net_margin_value = 0

                # Search through the dictionary for the right keys
                for key, value in latest_ratios.items():
                    if isinstance(key, tuple):
                        # Multi-level column from vnstock - check in any part of the tuple
                        key_str = str(key)
                        if 'P/E' in key_str:
                            pe_value = value if value and value != 0 else 0
                        elif 'P/B' in key_str:
                            pb_value = value if value and value != 0 else 0
                        elif 'P/S' in key_str:
                            ps_value = value if value and value != 0 else 0
                        elif 'ROE' in key_str:
                            roe_value = value if value and value != 0 else 0
                        elif 'ROA' in key_str:
                            roa_value = value if value and value != 0 else 0
                        elif 'Net Profit Margin' in key_str:
                            net_margin_value = value if value and value != 0 else 0
                    else:
                        # Simple column name fallback
                        if key == 'P/E':
                            pe_value = value if value and value != 0 else 0
                        elif key == 'P/B':
                            pb_value = value if value and value != 0 else 0
                        elif key == 'P/S':
                            ps_value = value if value and value != 0 else 0
                        elif key in ['ROE', 'ROE (%)']:
                            roe_value = value if value and value != 0 else 0
                        elif key in ['ROA', 'ROA (%)']:
                            roa_value = value if value and value != 0 else 0

                analysis_data['financial_ratios'] = {
                    'pe': pe_value,
                    'pb': pb_value,
                    'ps': ps_value,
                    'roe': roe_value * 100 if roe_value < 1 else roe_value,  # Convert to percentage if needed
                    'roa': roa_value * 100 if roa_value < 1 else roa_value,  # Convert to percentage if needed
                    'roi': latest_ratios.get('ROI', 0),
                    'debtToEquity': latest_ratios.get(('Chỉ tiêu thanh khoản', 'Financial Leverage'), latest_ratios.get('Debt/Equity', 0)),
                    'currentRatio': latest_ratios.get('Current Ratio', 0),
                    'quickRatio': latest_ratios.get('Quick Ratio', 0),
                    'grossMargin': latest_ratios.get('Gross Margin', 0),
                    'operatingMargin': latest_ratios.get('Operating Margin', 0),
                    'netMargin': net_margin_value * 100 if net_margin_value < 1 else net_margin_value,  # Convert to percentage if needed
                    'assetTurnover': latest_ratios.get('Asset Turnover', 0),
                    'inventoryTurnover': latest_ratios.get('Inventory Turnover', 0),
                    'receivablesTurnover': latest_ratios.get('Receivables Turnover', 0)
                }
            else:
                analysis_data['financial_ratios'] = {}
                
            # Calculate additional derived ratios
            if analysis_data['financial_ratios'] and analysis_data['balance_sheet']:
                try:
                    # Working Capital
                    analysis_data['financial_ratios']['workingCapital'] = (
                        analysis_data['balance_sheet'].get('currentAssets', 0) - 
                        analysis_data['balance_sheet'].get('currentLiabilities', 0)
                    )
                    
                    # Book Value per Share (approximate)
                    if analysis_data['company_info'].get('marketCap', 0) > 0:
                        analysis_data['financial_ratios']['bookValuePerShare'] = (
                            analysis_data['balance_sheet'].get('totalEquity', 0) / 
                            (analysis_data['company_info'].get('marketCap', 1) / 1000000)  # Rough approximation
                        )
                except Exception as e:
                    logger.warning(f"Error calculating derived ratios: {e}")
                    
        except Exception as e:
            logger.warning(f"Error getting financial ratios for {symbol}: {e}")
            analysis_data['financial_ratios'] = {}
        
        # 4. Growth Metrics (Year over Year)
        try:
            # Get historical data for growth calculation
            income_history = service.get_income_statement(symbol, period=Period.YEAR.value)

            if not income_history.empty and len(income_history) >= 2:
                # Sort by year to ensure correct order (latest year first)
                income_sorted = income_history.sort_values('yearReport', ascending=False)

                # Get the two most recent years
                current_year = income_sorted.iloc[0]  # Most recent year
                previous_year = income_sorted.iloc[1]  # Previous year

                def calculate_growth(current, previous):
                    if previous != 0:
                        return ((current - previous) / abs(previous)) * 100
                    return 0

                # Use the correct column names from vnstock data
                analysis_data['growth_metrics'] = {
                    'revenueGrowth': calculate_growth(
                        current_year.get('Revenue (Bn. VND)', 0),
                        previous_year.get('Revenue (Bn. VND)', 0)
                    ),
                    'earningsGrowth': calculate_growth(
                        current_year.get('Net Profit For the Year', current_year.get('Attributable to parent company', 0)),
                        previous_year.get('Net Profit For the Year', previous_year.get('Attributable to parent company', 0))
                    ),
                    'epsGrowth': calculate_growth(
                        current_year.get('EPS_basis', 0),
                        previous_year.get('EPS_basis', 0)
                    )
                }
            else:
                analysis_data['growth_metrics'] = {
                    'revenueGrowth': 0,
                    'earningsGrowth': 0,
                    'epsGrowth': 0
                }
                
        except Exception as e:
            logger.warning(f"Error calculating growth metrics for {symbol}: {e}")
            analysis_data['growth_metrics'] = {}
        
        # 5. Dividend Information
        try:
            dividends = service.get_dividends(symbol)
            
            if not dividends.empty:
                analysis_data['dividends'] = {
                    'lastDividend': dividends.iloc[-1].get('dividend', 0) if len(dividends) > 0 else 0,
                    'dividendYield': dividends.iloc[-1].get('yield', 0) if len(dividends) > 0 else 0,
                    'payoutRatio': dividends.iloc[-1].get('payoutRatio', 0) if len(dividends) > 0 else 0,
                    'dividendHistory': dividends.tail(5).to_dict('records') if len(dividends) > 0 else []
                }
            else:
                analysis_data['dividends'] = {
                    'lastDividend': 0,
                    'dividendYield': 0,
                    'payoutRatio': 0,
                    'dividendHistory': []
                }
                
        except Exception as e:
            logger.warning(f"Error getting dividend info for {symbol}: {e}")
            analysis_data['dividends'] = {}
        
        # 6. Ownership and Insider Information
        try:
            shareholders = service.get_shareholders(symbol)
            insider_trading = service.get_insider_trading(symbol)
            
            if not shareholders.empty:
                analysis_data['ownership'] = {
                    'majorShareholders': shareholders.head(10).to_dict('records'),
                    'institutionalOwnership': shareholders[shareholders['type'] == 'institutional']['percentage'].sum() if 'type' in shareholders.columns else 0
                }
            else:
                analysis_data['ownership'] = {
                    'majorShareholders': [],
                    'institutionalOwnership': 0
                }
                
            if not insider_trading.empty:
                analysis_data['insiderTrading'] = insider_trading.head(10).to_dict('records')
            else:
                analysis_data['insiderTrading'] = []
                
        except Exception as e:
            logger.warning(f"Error getting ownership info for {symbol}: {e}")
            analysis_data['ownership'] = {}
            analysis_data['insiderTrading'] = []
        
        # 7. Valuation Summary
        try:
            # Create a valuation summary based on available data
            valuation_summary = {
                'status': 'neutral',
                'score': 50,
                'factors': []
            }
            
            # PE Ratio analysis
            if analysis_data.get('financial_ratios', {}).get('pe'):
                pe = analysis_data['financial_ratios']['pe']
                if pe > 0 and pe < 15:
                    valuation_summary['factors'].append({'factor': 'P/E Ratio', 'status': 'undervalued', 'value': pe})
                    valuation_summary['score'] += 10
                elif pe > 30:
                    valuation_summary['factors'].append({'factor': 'P/E Ratio', 'status': 'overvalued', 'value': pe})
                    valuation_summary['score'] -= 10
                else:
                    valuation_summary['factors'].append({'factor': 'P/E Ratio', 'status': 'fair', 'value': pe})
            
            # ROE analysis
            if analysis_data.get('financial_ratios', {}).get('roe'):
                roe = analysis_data['financial_ratios']['roe']
                if roe > 15:
                    valuation_summary['factors'].append({'factor': 'ROE', 'status': 'strong', 'value': roe})
                    valuation_summary['score'] += 10
                elif roe < 5:
                    valuation_summary['factors'].append({'factor': 'ROE', 'status': 'weak', 'value': roe})
                    valuation_summary['score'] -= 10
                else:
                    valuation_summary['factors'].append({'factor': 'ROE', 'status': 'moderate', 'value': roe})
            
            # Debt to Equity analysis
            if analysis_data.get('financial_ratios', {}).get('debtToEquity'):
                de = analysis_data['financial_ratios']['debtToEquity']
                if de < 0.5:
                    valuation_summary['factors'].append({'factor': 'Debt/Equity', 'status': 'low', 'value': de})
                    valuation_summary['score'] += 5
                elif de > 2:
                    valuation_summary['factors'].append({'factor': 'Debt/Equity', 'status': 'high', 'value': de})
                    valuation_summary['score'] -= 5
                else:
                    valuation_summary['factors'].append({'factor': 'Debt/Equity', 'status': 'moderate', 'value': de})
            
            # Revenue Growth analysis
            if analysis_data.get('growth_metrics', {}).get('revenueGrowth'):
                growth = analysis_data['growth_metrics']['revenueGrowth']
                if growth > 10:
                    valuation_summary['factors'].append({'factor': 'Revenue Growth', 'status': 'strong', 'value': f"{growth:.1f}%"})
                    valuation_summary['score'] += 10
                elif growth < 0:
                    valuation_summary['factors'].append({'factor': 'Revenue Growth', 'status': 'negative', 'value': f"{growth:.1f}%"})
                    valuation_summary['score'] -= 10
                else:
                    valuation_summary['factors'].append({'factor': 'Revenue Growth', 'status': 'moderate', 'value': f"{growth:.1f}%"})
            
            # Determine overall status
            if valuation_summary['score'] >= 70:
                valuation_summary['status'] = 'bullish'
            elif valuation_summary['score'] <= 30:
                valuation_summary['status'] = 'bearish'
            else:
                valuation_summary['status'] = 'neutral'
            
            analysis_data['valuation_summary'] = valuation_summary
            
        except Exception as e:
            logger.warning(f"Error creating valuation summary for {symbol}: {e}")
            analysis_data['valuation_summary'] = {
                'status': 'neutral',
                'score': 50,
                'factors': []
            }
        
        # Add timestamp
        analysis_data['timestamp'] = datetime.now().isoformat()
        analysis_data['symbol'] = symbol
        
        return Response(analysis_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in fundamental analysis for {symbol}: {e}")
        return Response(
            {'error': f'Failed to get fundamental analysis for {symbol}', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['GET'])
def get_financial_statements(request, symbol):
    """
    Get detailed financial statements for a stock
    
    Args:
        symbol: Stock ticker symbol
        period: 'year' or 'quarter' (optional, default: 'year')
        
    Returns:
        JSON response with income statement, balance sheet, and cash flow
    """
    try:
        period = request.GET.get('period', 'year')
        
        # Initialize stock service
        service = StockService(symbol=symbol, source=DataSource.VCI.value)
        
        # Get financial statements
        income_statement = service.get_income_statement(symbol, period=period)
        balance_sheet = service.get_balance_sheet(symbol, period=period)
        cash_flow = service.get_cash_flow(symbol, period=period)
        
        # Convert to dictionaries
        response_data = {
            'symbol': symbol,
            'period': period,
            'income_statement': income_statement.to_dict('records') if not income_statement.empty else [],
            'balance_sheet': balance_sheet.to_dict('records') if not balance_sheet.empty else [],
            'cash_flow': cash_flow.to_dict('records') if not cash_flow.empty else [],
            'timestamp': datetime.now().isoformat()
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting financial statements for {symbol}: {e}")
        return Response(
            {'error': f'Failed to get financial statements for {symbol}', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['GET'])
def compare_fundamental_ratios(request):
    """
    Compare fundamental ratios between multiple stocks
    
    Query Parameters:
        symbols: Comma-separated list of stock symbols (e.g., 'VIC,VNM,TCB')
        
    Returns:
        JSON response with ratio comparison
    """
    try:
        symbols_param = request.GET.get('symbols', '')
        
        if not symbols_param:
            return Response(
                {'error': 'Please provide symbols parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        symbols = [s.strip() for s in symbols_param.split(',')]
        
        # Initialize stock service
        service = StockService(source=DataSource.VCI.value)
        
        # Compare ratios
        comparison = service.compare_financial_ratios(
            symbol_list=symbols,
            industry_comparison=True,
            frequency=Period.YEAR.value,
            start_year=2020
        )
        
        response_data = {
            'symbols': symbols,
            'comparison': comparison.to_dict('records') if not comparison.empty else [],
            'timestamp': datetime.now().isoformat()
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error comparing fundamental ratios: {e}")
        return Response(
            {'error': 'Failed to compare fundamental ratios', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )