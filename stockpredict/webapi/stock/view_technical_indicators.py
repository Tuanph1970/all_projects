from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from repositories.technical_repository import TechnicalRepository
@api_view(['GET'])
def get_indicator_by_group(request, group_name):
    if request.method == 'GET':
        tech_repo = TechnicalRepository()
        result = tech_repo.get_technical_indicators_by_group_name(group_name)
        return Response(result)

@api_view(['GET'])
def get_indicator_parameters(request):
    if request.method == 'GET':
        tech_repo = TechnicalRepository()
        result = tech_repo.get_technical_indicator_params()
        return Response(result)