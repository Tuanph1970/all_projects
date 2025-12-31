from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser

from services.agent_service import AgentService
from services.ml_agent_service import MLAgentService
@api_view(['GET'])
def getDefaultAgents(request):
    if request.method == 'GET':
        agent_service = AgentService()
        ret = agent_service.get_all_agents()
        return Response(ret)


@api_view(['POST'])
def run_agent(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        agent_service = AgentService()
        ret = agent_service.run_stock_agent(data)
        return Response(ret)

@api_view(['POST'])
def run_ml_agent(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        ml_agent_service = MLAgentService()
        ret = ml_agent_service.run_ml_stock_agent(data)
        return Response(ret)



