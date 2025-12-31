import logging
import threading
import time

from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser

from services.solution_service import SolutionService
from services.stock_market_service import StockMarketService
from repositories.portfolio_repository import PortfolioRepository
from core.authentication import jwt_required
from core.exceptions import SolutionTrainingException

logger = logging.getLogger(__name__)

# Global dictionary to track training status
training_status = {}


@api_view(['GET'])
@jwt_required
def get_solutions(request):
    """Get solutions created by the logged-in user"""
    if request.method == 'GET':
        solution_service = SolutionService()
        # Get the logged-in user
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(request.user.id)
            data = solution_service.get_solutions_by_user(user_id)
        else:
            # If user is not authenticated, return empty list
            data = []
        return Response(data)

@api_view(['GET'])
@jwt_required
def get_predict_tickers(request):
    """
    Get tickers available for prediction/training.
    Returns only stocks from user's portfolio.
    """
    if request.method == 'GET':
        # Get user ID from authenticated request
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        user_id = request.user.id

        # Get user's portfolio symbols
        portfolio_repo = PortfolioRepository()
        portfolio_symbols = portfolio_repo.get_user_portfolio_symbols(user_id)

        if not portfolio_symbols:
            logger.info(f"User {user_id} has no stocks in portfolio")
            return Response([])

        # Get company info for all stocks (not just VN100)
        stock_service = StockMarketService()
        all_companies = stock_service.get_all_companies()

        # Filter to only include stocks from user's portfolio
        filtered_companies = [
            company for company in all_companies
            if company.get('ticker', '').upper() in portfolio_symbols
        ]

        logger.info(f"User {user_id}: {len(filtered_companies)} portfolio stocks available for prediction")
        return Response(filtered_companies)

@api_view(['GET'])
def get_predict_models(request):
    if request.method == 'GET':
        solution_service = SolutionService()
        data = solution_service.get_predict_models()
        return Response(data)

@api_view(['GET'])
def get_predict_covariates(request):
    if request.method == 'GET':
        solution_service = SolutionService()
        data = solution_service.get_predict_covariates()
        return Response(data)

@api_view(['POST'])
@jwt_required
def create_predict_solution(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        solution_service = SolutionService()
        # Get the logged-in user and add to data
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(request.user.id)
            data['user_id'] = user_id
            # Set created_by if not provided
            if 'created_by' not in data:
                data['created_by'] = user_id
        solution_id = solution_service.create_solution(data)
        # Return the created solution with its ID
        created_solution = {**data, 'id': solution_id}
        return Response(created_solution, status=status.HTTP_201_CREATED)

@api_view(['PUT'])
@jwt_required
def update_predict_solution(request):
    if request.method == 'PUT':
        data = JSONParser().parse(request)
        solution_service = SolutionService()
        # Get the logged-in user and add to data
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(request.user.id)
            data['user_id'] = user_id
            # Set updated_by if not provided
            if 'updated_by' not in data:
                data['updated_by'] = user_id
        solution_service.update_solution(data)
        # Return the updated solution
        return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
@jwt_required
def get_solution_by_id(request, id=0):
    if request.method == 'GET':
        solution_service = SolutionService()
        ret = solution_service.get_solution_by_id(id)
        return Response(ret)

@api_view(['DELETE'])
@jwt_required
def delete_solution_by_id(request, id=0):
    if request.method == 'DELETE':
        solution_service = SolutionService()
        solution_service.delete_solution(id)
        return Response(status=status.HTTP_200_OK)

def run_training_async(solution_id, data, solution_service):
    """Background function to run training asynchronously"""
    try:
        training_status[solution_id] = {
            'status': 'training',
            'message': 'Training in progress...',
            'progress': 0,
            'started_at': time.time()
        }

        # Run the actual training
        ret = solution_service.train_solution(data)

        # Update status on success
        training_status[solution_id] = {
            'status': 'completed',
            'message': 'Training completed successfully',
            'result': ret,
            'completed_at': time.time()
        }
    except SolutionTrainingException as e:
        # Update status on error
        training_status[solution_id] = {
            'status': 'failed',
            'message': str(e),
            'error': str(e),
            'solution_id': e.solution_id,
            'suggestions': e.suggestions,
            'failed_at': time.time()
        }
    except Exception as e:
        # Update status on unexpected error
        training_status[solution_id] = {
            'status': 'failed',
            'message': f'Training failed: {str(e)}',
            'error': str(e),
            'failed_at': time.time()
        }

@api_view(['POST'])
@jwt_required
def train_solution(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        solution_id = data.get('id')

        # Check if this solution is already training
        if solution_id in training_status:
            current_status = training_status[solution_id]
            if current_status['status'] == 'training':
                return Response({
                    'message': 'Training already in progress',
                    'status': 'training',
                    'solution_id': solution_id
                }, status=status.HTTP_200_OK)

        # Start training in background thread
        solution_service = SolutionService()
        training_thread = threading.Thread(
            target=run_training_async,
            args=(solution_id, data, solution_service)
        )
        training_thread.daemon = True
        training_thread.start()

        # Return immediately with status
        return Response({
            'message': 'Training started successfully',
            'status': 'training',
            'solution_id': solution_id
        }, status=status.HTTP_202_ACCEPTED)

@api_view(['GET'])
@jwt_required
def get_training_status(request, solution_id):
    """Get the current training status for a solution"""
    if solution_id not in training_status:
        return Response({
            'status': 'not_found',
            'message': 'No training session found for this solution'
        }, status=status.HTTP_404_NOT_FOUND)

    current_status = training_status[solution_id]

    # Clean up old completed/failed statuses after 5 minutes
    if current_status['status'] in ['completed', 'failed']:
        status_time = current_status.get('completed_at') or current_status.get('failed_at', 0)
        if time.time() - status_time > 300:  # 5 minutes
            del training_status[solution_id]

    return Response(current_status, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_ticker_time_range(request, ticker=''):
    if request.method == 'GET':
        from services.stock_market_service import CompanyService
        company_service = CompanyService()
        df = company_service.get_price_history_df(symbol=ticker, source="VCI")
        if len(df.index) >= 0:
            start_date = df['time'].values[0]
            end_date = df['time'].values[-1]
            import pandas as pd
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
            ret = {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d')
            }
            return Response(ret)
        return Response({})

@api_view(['POST'])
@jwt_required
def predict_solution(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        solution_service = SolutionService()
        ret = solution_service.predict_solution(data)
        return Response(ret)

@api_view(['POST'])
def calculate_date_range(request):
    """
    Calculate recommended date range for model training.

    Request body:
    {
        "model_id": int,
        "start_date": "YYYY-MM-DD" (optional),
        "end_date": "YYYY-MM-DD" (optional),
        "validation": bool (default: true),
        "train_ratio": float (default: 0.8),
        "ticker": str (optional)
    }

    Response:
    {
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "required_points": int,
        "recommended_points": int,
        "estimated_points": int,
        "adjusted": bool,
        "requirements": {...},
        "message": str
    }
    """
    if request.method == 'POST':
        data = JSONParser().parse(request)
        solution_service = SolutionService()
        try:
            result = solution_service.calculate_recommended_date_range(data)
            return Response(result)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )