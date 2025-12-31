from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
import json

from TechnicalAnalysis.TechnicalIndicator import TechnicalIndicator
from services.stock_market_service import StockMarketService, CompanyService, FinancialService
from services.model_service import ModelService
from services.technical_analysis_service import TechnicalAnalysisService
from repositories.stock_repository import MarketIndexRepository, LatestIndicesRepository
from core.exceptions import EntityNotFoundException, ValidationException, ExternalServiceException, ModelCreationException
from core.database import get_database_connection
from core.authentication import jwt_required
from Models.Common import get_all_predict_model, get_model_parameters, getModelParameterDetail, \
    get_model_parameters_by_id, create_rnn_model, save_rnn_model, create_blockrnn_model, save_blockrnn_model


@api_view(['GET'])
def ApiOverview(request):
    api_urls = {
        'all_items': '/',
        'Search by Category': '/?category=category_name',
        'Search by Subcategory': '/?subcategory=category_name',
        'Add': '/create',
        'Update': '/update/pk',
        'Delete': '/item/pk/delete'
    }

    return Response(api_urls)

@api_view(['GET'])
def get_company_by_group(request, group):
    if request.method == 'GET':
        try:
            service = StockMarketService()
            json_data = service.get_companies_by_group(group=group)
            return Response(json_data)
        except ExternalServiceException as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
def get_all_companies(request):
    if request.method == 'GET':
        try:
            service = StockMarketService()
            json_data = service.get_all_companies()
            return Response(json_data)
        except ExternalServiceException as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
def get_companies_by_industry(request, industry_id):
    if request.method == 'GET':
        try:
            service = StockMarketService()
            json_data = service.get_companies_by_industry(industry_id=int(industry_id))
            return Response(json_data)
        except (ExternalServiceException, ValueError) as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
def get_top_gainers(request):
    if request.method == 'GET':
        try:
            service = StockMarketService()
            json_data = service.get_top_gainers()
            return Response(json_data)
        except ExternalServiceException as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
def get_top_losers(request):
    if request.method == 'GET':
        try:
            service = StockMarketService()
            json_data = service.get_top_losers()
            return Response(json_data)
        except ExternalServiceException as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
def get_top_actives(request):
    if request.method == 'GET':
        try:
            service = StockMarketService()
            json_data = service.get_top_actives()
            return Response(json_data)
        except ExternalServiceException as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
def get_industries(request):
    symbol = "VN30F1M"
    source = "VCI"
    if request.method == 'GET':
        service = StockMarketService()
        json_data = service.get_industries(symbol=symbol,source=source)
        return Response(json_data)
@api_view(['GET'])
def viewPriceBoardApi(request,id=0):
    symbol = "VN30F1M"
    source = "VCI"
    group = "VN30"
    if request.method == 'GET':
        service = StockMarketService()
        json_data = service.get_price_boards(symbol=symbol,source=source,group=group)
        return Response(json_data)
@api_view(['GET'])
def viewCompanyOverview(request,ticker):
    if request.method == 'GET':
        source = "VCI"
        service = CompanyService()
        json_data = service.get_company_overview(symbol=ticker,source=source)
        return Response(json_data)
@api_view(['GET'])
def viewCompanyProfile(request,ticker):
    if request.method == 'GET':
        source = "VCI"
        service = CompanyService()
        json_data = service.get_company_profile(symbol=ticker,source=source)
        return Response(json_data)
@api_view(['GET'])
def viewCompanyEvents(request,ticker):
    if request.method == 'GET':
        source = "VCI"
        service = CompanyService()
        json_data = service.get_company_events(symbol=ticker,source=source)
        return Response(json_data)
@api_view(['GET'])
def viewCompanyNews(request,ticker):
    if request.method == 'GET':
        source = "VCI"
        service = CompanyService()
        json_data = service.get_company_news(symbol=ticker,source=source)
        return Response(json_data)
@api_view(['GET'])
def viewCompanyDividends(request,ticker):
    if request.method == 'GET':
        source = "VCI"
        service = CompanyService()
        json_data = service.get_company_dividends(symbol=ticker,source=source)
        return Response(json_data)


@api_view(['GET'])
def viewFinancialReportIncomeStatement(request,symbol):
    if request.method == 'GET':
        language = "en"
        period = "quarter"
        source = "VCI"
        service = FinancialService()
        json_data = service.get_financial_income_statement(symbol=symbol,source=source,period=period,language=language)
        return Response(json_data)
@api_view(['GET'])
def viewFinancialReportCashFlow(request,symbol):
    if request.method == 'GET':
        language = "en"
        period = "quarter"
        source = "VCI"
        service = FinancialService()
        json_data = service.get_financial_cash_flow(symbol=symbol, source=source, period=period,
                                                                    language=language)
        return Response(json_data)
@api_view(['GET'])
def viewFinancialReportBalanceSheet(request,symbol):
    if request.method == 'GET':
        language = "en"
        period = "quarter"
        source = "VCI"
        service = FinancialService()
        json_data = service.get_company_balance_sheet(symbol=symbol, source=source, period=period,
                                                                    language=language)
        return Response(json_data)
@api_view(['GET'])
def viewFinancialRatio(request,symbol):
    if request.method == 'GET':
        language = "en"
        period = "quarter"
        source = "VCI"
        service = FinancialService()
        json_data = service.get_company_financial_ratio(symbol=symbol, source=source, period=period,
                                                                    language=language)
        return Response(json_data)

@api_view(['GET'])
def viewMarketIndexSeries(request):
    if request.method == 'GET':
        try:
            repo = MarketIndexRepository()
            json_data = repo.get_market_index_series()
            return Response(json_data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
def viewMarketLatestIndicesSeries(request):
    if request.method == 'GET':
        try:
            repo = LatestIndicesRepository()
            json_data = repo.get_latest_indices_series()
            return Response(json_data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def getAllHistoricalData(request,ticker):
    if request.method == 'GET':
        service = CompanyService()

        # Check if start_date and end_date query parameters are provided
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        if start_date and end_date:
            # Use filtered data with date range
            json_data = service.get_price_history(symbol=ticker, source='VCI', start=start_date, end=end_date)
        else:
            # Get all historical data
            json_data = service.get_all_history_data(symbol=ticker, source="VCI")

        return Response(json_data)

@api_view(['POST'])
def getCompanyHistoricalData(request):
    if request.method == 'POST':
        post_data = JSONParser().parse(request)
        ticker = post_data['ticker']
        start = post_data['start']
        end = post_data['end']
        service = CompanyService()
        json_data = service.get_price_history(symbol=ticker,source='VCI',start=start,end=end)
        return Response(json_data)
@api_view(['POST'])
def getMACD(request):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            service = TechnicalAnalysisService()
            ret = service.get_macd(
                ticker=data['ticker'],
                fast=data['fast'],
                slow=data['slow'],
                signal=data['signal'],
                start=data['start'],
                end=data['end']
            )
            return Response(ret)
        except (ExternalServiceException, KeyError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
@api_view(['POST'])
def getSMA(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        ticker = data['ticker']
        length = data['length']
        start = data['start']
        end = data['end']
        techindicator = TechnicalIndicator()
        ret = techindicator.getSMA(ticker=ticker,length=length,start=start,end=end)
        return Response(ret)
@api_view(['POST'])
def getEMA(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        ticker = data['ticker']
        length = data['length']
        start = data['start']
        end = data['end']

        techindicator = TechnicalIndicator()
        ret = techindicator.getEMA(ticker=ticker,length=length,start=start,end=end)

        return Response(ret)

@api_view(['POST'])
def getCandleStick(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        ticker = data['ticker']
        startTime = data['start']
        endTime = data['end']
        service = CompanyService()
        df = service.get_price_history_df(ticker,"VCI",start=startTime,end=endTime)
        df = df[['time','open','high','low','close']]
        json_str = df.to_json(orient='records', force_ascii=False, date_format='iso')
        return Response(json.loads(json_str))

@api_view(['POST'])
def getVolume(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        ticker = data['ticker']
        startTime = data['start']
        endTime = data['end']
        service = CompanyService()
        df = service.get_price_history_df(ticker,"VCI",start=startTime,end=endTime)
        df_ret = df[['time','volume']]
        json_str = df_ret.to_json(orient='records', force_ascii=False, date_format='iso')
        return Response(json.loads(json_str))
@api_view(['POST'])
def getPSAR(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        ticker = data['ticker']
        start = data['start']
        end = data['end']

        techindicator = TechnicalIndicator()
        ret = techindicator.getParabolicSARIndicator(ticker=ticker,start=start,end=end)

        return Response(ret)

@api_view(['POST'])
def getRSI(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        ticker = data['ticker']
        length = data['length']
        start = data['start']
        end = data['end']

        techindicator = TechnicalIndicator()
        ret = techindicator.getRSI(ticker=ticker,length=length,start=start,end=end)

        return Response(ret)
@api_view(['GET'])
def getPredictModels(request):
    if request.method == 'GET':
        try:
            service = ModelService()
            predict_models = get_all_predict_model()
            supported_models = service.get_supported_model_types()
            return Response({
                'all_models': predict_models,
                'supported_factory_models': supported_models
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['POST'])
def getDefaultModelParameters(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        model = data['model']

        return Response(get_model_parameters(model))
@api_view(['POST','PUT'])
@jwt_required
def RNNModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="RNN",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="RNN", model_sub_type=data['model_sub_type'])
        res = save_rnn_model(data)
        return Response(res)
@api_view(['POST','PUT'])
@jwt_required
def BlockRNNModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="BlockRNN",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="BlockRNN", model_sub_type=data['model_sub_type'])
        res = save_blockrnn_model(data)
        return Response(res)
@api_view(['POST','PUT'])
@jwt_required
def CatBoostModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="CatBoost",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        from Models.Common import save_catboost_model
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="CatBoost")
        res = save_catboost_model(data)
        return Response(res)
@api_view(['POST','PUT'])
@jwt_required
def DLinearModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="DLinear",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        from Models.Common import save_dlinear_model
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="DLinear")
        res = save_dlinear_model(data)
        return Response(res)
@api_view(['POST','PUT'])
@jwt_required
def LightGBMModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="LightGBM",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        from Models.Common import save_lightgbm_model
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="LightGBM")
        res = save_lightgbm_model(data)
        return Response(res)
@api_view(['POST','PUT'])
@jwt_required
def NBeatsModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="NBeats",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        from Models.Common import save_nbeats_model
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="NBeats")
        res = save_nbeats_model(data)
        return Response(res)
@api_view(['POST','PUT'])
@jwt_required
def NHitsModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="NHits",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        from Models.Common import save_nhits_model
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="NHits")
        res = save_nhits_model(data)
        return Response(res)
@api_view(['POST','PUT'])
@jwt_required
def NLinearModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="NLinear",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        from Models.Common import save_nlinear_model
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="NLinear")
        res = save_nlinear_model(data)
        return Response(res)
@api_view(['POST','PUT'])
@jwt_required
def RandomForestModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="RandomForest",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        from Models.Common import save_randomforest_model
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="RandomForest")
        res = save_randomforest_model(data)
        return Response(res)
@api_view(['POST','PUT'])
@jwt_required
def TCNModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="TCN",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        from Models.Common import save_tcn_model
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="TCN")
        res = save_tcn_model(data)
        return Response(res)
@api_view(['POST','PUT'])
@jwt_required
def TFTModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="TFT",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        from Models.Common import save_tft_model
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="TFT")
        res = save_tft_model(data)
        return Response(res)
@api_view(['POST','PUT'])
@jwt_required
def TiDEModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="TiDE",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        from Models.Common import save_tide_model
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="TiDE")
        res = save_tide_model(data)
        return Response(res)
@api_view(['POST','PUT'])
@jwt_required
def TransformerModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="Transformer",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        from Models.Common import save_transformer_model
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="Transformer")
        res = save_transformer_model(data)
        return Response(res)
@api_view(['POST','PUT'])
@jwt_required
def XGBoostModel(request):
    data = JSONParser().parse(request)
    if request.method == 'POST':
        model_service = ModelService()
        # Get the logged-in user
        user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else 'default_user'
        created_by = user_id

        # Extract configuration parameters (exclude metadata fields)
        parameters = {k: v for k, v in data.items()
                     if k not in ['model_name', 'model_type', 'model_sub_type']}

        result = model_service.create_model(
            model_name=data['model_name'],
            model_type="XGBoost",
            model_sub_type=data.get('model_sub_type'),
            parameters=parameters,
            created_by=created_by,
            user_id=user_id
        )
        return Response(result)
    elif request.method == 'PUT':
        from Models.Common import save_xgboost_model
        model_service = ModelService()
        model_service.update_model(data['model_id'], model_name=data['model_name'], model_type="XGBoost")
        res = save_xgboost_model(data)
        return Response(res)
@api_view(['GET'])
@jwt_required
def get_models(request):
    """Get model instances created by the logged-in user"""
    if request.method == 'GET':
        try:
            service = ModelService()
            # Get the logged-in user
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_id = str(request.user.id)
                data = service.get_models_by_user(user_id)
            else:
                # If user is not authenticated, return empty list
                data = []
            return Response(data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_model_types(request):
    """Get all available model types with their sub-models from tbl_all_models"""
    if request.method == 'GET':
        try:
            service = ModelService()
            data = service.get_all_model_types(active_only=True)
            return Response(data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
def delete_model(request, id):
    if request.method == 'DELETE':
        try:
            service = ModelService()
            success = service.delete_model(int(id))
            if success:
                return Response(status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Model not found'}, status=status.HTTP_404_NOT_FOUND)
        except (EntityNotFoundException, ValueError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def getModelById(request,id=0):
    if request.method == 'GET' :

        conn = get_database_connection()
        if id != 0:
            cur = conn.cursor()
            sqlQuery = "SELECT model_name,model_type,model_sub_type,past_covariate,future_covariate FROM model_instances WHERE id= " + str(id)
            cur.execute(sqlQuery)
            records = cur.fetchall()
            row = records[0]
            model_name = row[0]
            model_type = row[1]
            model_sub_type = row[2]
            past_covariate = row[3]
            future_covariate = row[4]
            json_data = get_model_parameters_by_id(id,model_name,model_type)
            json_data['model_name'] = model_name
            json_data['model_type'] = model_type
            json_data['model_sub_type'] = model_sub_type
            json_data['past_covariate'] = past_covariate
            json_data['future_covariate'] = future_covariate
            return Response(json_data)
        else:
            return Response(status=status.HTTP_200_OK)
@api_view(['GET'])
def get_model_parameters_detail(request,model_type):
    if request.method == 'GET':
        json_data = getModelParameterDetail(model_type)
        return Response(json_data)
@api_view(['GET'])
def get_model_parameter_fields(request):
    if request.method == 'GET':
        model_service = ModelService()
        json_data = model_service.get_model_parameter_fields()
        return Response(json_data)
@api_view(['GET'])
def getModelsDefaultParamters(request):
    if request.method == 'GET':
        model_service = ModelService()
        json_data = model_service.get_model_default_parameters()
        return Response(json_data)


@api_view(['GET'])
def get_options_by_parameter(request):
    if request.method == 'GET':
        model_service = ModelService()
        json_data = model_service.get_options_by_parameter()
        return Response(json_data)


        












