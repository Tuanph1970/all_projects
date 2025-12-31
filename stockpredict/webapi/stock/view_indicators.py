from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser

from services.indicator_service import IndicatorService


@api_view(['GET'])
def get_all_indicators(request):
    """Get all technical indicators grouped by category"""
    if request.method == 'GET':
        indicator_service = IndicatorService()
        data = indicator_service.get_all_indicators()
        return Response(data)


@api_view(['GET'])
def get_indicators_by_type(request, indicator_type):
    """Get indicators filtered by type (trend, momentum, volatility, volume)"""
    if request.method == 'GET':
        indicator_service = IndicatorService()
        data = indicator_service.get_indicators_by_type(indicator_type)
        return Response(data)


@api_view(['GET'])
def get_indicator_by_id(request, indicator_id):
    """Get specific indicator details"""
    if request.method == 'GET':
        indicator_service = IndicatorService()
        data = indicator_service.get_indicator_by_id(indicator_id)
        return Response(data)


@api_view(['POST'])
def calculate_indicator(request):
    """
    Calculate indicator values for given symbol and date range
    POST body: {
        'indicator_name': str,
        'symbol': str,
        'start_date': str,
        'end_date': str,
        'custom_params': dict (optional)
    }
    """
    if request.method == 'POST':
        data = JSONParser().parse(request)
        indicator_service = IndicatorService()
        result = indicator_service.calculate_indicator_values(data)
        return Response(result)


@api_view(['GET'])
def get_solution_indicators(request, solution_id):
    """Get all indicators configured for a solution"""
    if request.method == 'GET':
        indicator_service = IndicatorService()
        data = indicator_service.get_solution_indicators(solution_id)
        return Response(data)


@api_view(['POST'])
def add_solution_indicator(request, solution_id):
    """
    Add an indicator to a solution
    POST body: {
        'indicator_id': int,
        'indicator_category': str (or 'indicator_type' for backward compatibility),
        'covariate_type': str (optional, default 'past'),
        'parameters': dict (optional)
    }
    """
    if request.method == 'POST':
        data = JSONParser().parse(request)
        data['solution_id'] = solution_id
        indicator_service = IndicatorService()
        result_id = indicator_service.add_solution_indicator(data)
        return Response({'id': result_id}, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
def update_solution_indicator(request, solution_id, indicator_id):
    """
    Update indicator parameters for a solution
    PUT body: {
        'parameters': dict
    }
    """
    if request.method == 'PUT':
        data = JSONParser().parse(request)
        data['solution_id'] = solution_id
        data['indicator_id'] = indicator_id
        indicator_service = IndicatorService()
        result = indicator_service.update_solution_indicator(data)
        if result:
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
def remove_solution_indicator(request, solution_id, indicator_id):
    """Remove an indicator from a solution"""
    if request.method == 'DELETE':
        indicator_service = IndicatorService()
        result = indicator_service.remove_solution_indicator(solution_id, indicator_id)
        if result:
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def set_solution_indicators(request, solution_id):
    """
    Set all four indicators for a solution at once
    POST body: {
        'trend_indicator': {'id': int, 'covariate_type': str, 'parameters': dict},
        'momentum_indicator': {'id': int, 'covariate_type': str, 'parameters': dict},
        'volatility_indicator': {'id': int, 'covariate_type': str, 'parameters': dict},
        'volume_indicator': {'id': int, 'covariate_type': str, 'parameters': dict}
    }

    covariate_type options: 'past', 'future', 'both' (default: 'past')
    """
    if request.method == 'POST':
        data = JSONParser().parse(request)
        data['solution_id'] = solution_id
        indicator_service = IndicatorService()
        result = indicator_service.set_solution_indicators(data)
        return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
def calculate_solution_indicators(request, solution_id):
    """
    Calculate all indicators for a solution
    POST body: {
        'symbol': str,
        'start_date': str,
        'end_date': str
    }
    """
    if request.method == 'POST':
        data = JSONParser().parse(request)
        data['solution_id'] = solution_id
        indicator_service = IndicatorService()
        result = indicator_service.calculate_solution_indicators(data)
        return Response(result)


@api_view(['GET'])
def validate_solution_indicators(request, solution_id):
    """Validate that a solution has all required indicators configured"""
    if request.method == 'GET':
        indicator_service = IndicatorService()
        result = indicator_service.validate_solution_indicators(solution_id)
        return Response(result)


@api_view(['POST'])
def create_indicator(request):
    """
    Create a new technical indicator
    POST body: {
        'name': str,
        'type': str (trend, momentum, volatility, volume),
        'description': str,
        'calculation_function': str,
        'default_parameters': dict
    }
    """
    if request.method == 'POST':
        data = JSONParser().parse(request)
        indicator_service = IndicatorService()
        result = indicator_service.create_indicator(data)
        return Response(result, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
def update_indicator(request, indicator_id):
    """
    Update an existing technical indicator
    PUT body: {
        'name': str,
        'type': str,
        'description': str,
        'calculation_function': str,
        'default_parameters': dict
    }
    """
    if request.method == 'PUT':
        data = JSONParser().parse(request)
        indicator_service = IndicatorService()
        result = indicator_service.update_indicator(indicator_id, data)
        if result:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
def delete_indicator(request, indicator_id):
    """Delete a technical indicator"""
    if request.method == 'DELETE':
        indicator_service = IndicatorService()
        result = indicator_service.delete_indicator(indicator_id)
        if result:
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def check_covariate_compatibility(request, solution_id):
    """
    Check covariate type compatibility with solution's model
    GET /api/solutions/{solution_id}/covariate-compatibility

    Returns model capabilities and compatible covariate types
    """
    if request.method == 'GET':
        from services.solution_service import SolutionService

        solution_service = SolutionService()
        solution = solution_service.get_solution_by_id(solution_id)

        if not solution:
            return Response(
                {'error': f'Solution {solution_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        models = solution_service.get_predict_models()
        model = next((m for m in models if m['id'] == solution['model_id']), None)

        if not model:
            return Response(
                {'error': f'Model {solution["model_id"]} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        supports_past = bool(model.get('past_covariate', 0))
        supports_future = bool(model.get('future_covariate', 0))

        # Determine compatible covariate types
        compatible_types = []
        if supports_past:
            compatible_types.append('past')
        if supports_future:
            compatible_types.append('future')
        if supports_past and supports_future:
            compatible_types.append('both')

        return Response({
            'solution_id': solution_id,
            'solution_name': solution.get('solution_name'),
            'model_id': model['id'],
            'model_name': model['model_name'],
            'model_capabilities': {
                'supports_past_covariates': supports_past,
                'supports_future_covariates': supports_future
            },
            'compatible_covariate_types': compatible_types,
            'recommendations': {
                'past': 'Use for historical data features' if supports_past else 'Not supported by this model',
                'future': 'Use for known future events' if supports_future else 'Not supported by this model',
                'both': 'Use when feature is available in both past and future' if (supports_past and supports_future) else 'Not supported by this model'
            }
        })
