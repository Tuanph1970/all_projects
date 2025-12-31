"""
Django REST API Views for Stock Trading Simulation
"""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from services.simulation_service import SimulationService
from core.exceptions import SimulationException, ValidationException


@api_view(['POST'])
def run_simulation(request):
    """
    Run a stock trading simulation with ML prediction

    POST /api/simulation/run/
    {
        "ticker": "VNM",
        "start_date": "2023-01-01",
        "end_date": "2024-01-01",
        "model_type": "XGBoost",
        "initial_capital": 100000000,
        "model_params": {
            "lookback_period": 60,
            "n_estimators": 100
        },
        "trading_params": {
            "threshold_buy": 0.02,
            "threshold_sell": -0.01,
            "position_size": 0.3
        },
        "use_indicators": false,
        "indicator_names": ["SMA", "RSI"]
    }
    """
    try:
        data = JSONParser().parse(request)
        simulation_service = SimulationService()
        results = simulation_service.run_simulation(data)
        return Response(results, status=status.HTTP_200_OK)

    except ValidationException as e:
        return Response(
            {'error': 'Validation Error', 'message': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except SimulationException as e:
        return Response(
            {'error': 'Simulation Error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {'error': 'Unexpected Error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_available_models(request):
    """
    Get list of available ML models for prediction

    GET /api/simulation/models/
    """
    try:
        simulation_service = SimulationService()
        models = simulation_service.get_available_models()
        return Response(models, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': 'Error fetching models', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_simulation_template(request):
    """
    Get a template configuration for simulations

    GET /api/simulation/template/
    """
    try:
        simulation_service = SimulationService()
        template = simulation_service.get_simulation_config_template()
        return Response(template, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': 'Error fetching template', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_trained_solutions(request):
    """
    Get list of user's trained solutions that can be used for simulation

    GET /api/simulation/trained-solutions/
    Optional query parameter: user_id
    """
    try:
        user_id = request.GET.get('user_id', None)
        # If user is authenticated and no user_id provided, use their ID
        if not user_id and hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(request.user.id)

        simulation_service = SimulationService()
        solutions = simulation_service.get_trained_solutions(user_id)
        return Response(solutions, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': 'Error fetching trained solutions', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
