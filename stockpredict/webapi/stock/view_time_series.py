from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from services.time_series_service import TimeSeriesService
import pymysql

@api_view(['GET'])
def get_time_series(request):
    if request.method == 'GET':
        time_series_service = TimeSeriesService()
        data = time_series_service.get_all_time_series()
        return Response(data)

@api_view(['POST'])
def create_time_series(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        time_series_service = TimeSeriesService()
        time_series_service.add_time_series(data)
        return Response(status=status.HTTP_200_OK)

@api_view(['PUT'])
def update_time_series(request):
    if request.method == 'PUT':
        data = JSONParser().parse(request)
        time_series_service = TimeSeriesService()
        time_series_service.modify_time_series(data)
        return Response(status=status.HTTP_200_OK)

@api_view(['GET'])
def get_series_categories(request):
    if request.method == 'GET':
        time_series_service = TimeSeriesService()
        data = time_series_service.get_series_types()
        return Response(data)

@api_view(['GET'])
def get_seriesById(request, id=0):
    if request.method == 'GET':
        time_series_service = TimeSeriesService()
        data = time_series_service.get_series_by_id(id)
        return Response(data)

@api_view(['DELETE'])
def delete_series_by_id(request, id=0):
    if request.method == 'DELETE':
        time_series_service = TimeSeriesService()
        result = time_series_service.delete_series_by_id(id)
        if result["status"] == "success":
            return Response(status=status.HTTP_200_OK, data='OK')
        else:
            return Response(status=status.HTTP_200_OK, data='time series is used in solution')

@api_view(['POST'])
def get_series_by_ids(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        time_series_service = TimeSeriesService()
        ret = time_series_service.get_series_by_ids(data.get('time_series', []))
        return Response(ret)

@api_view(['PUT'])
def update_series_batch(request):
    if request.method == 'PUT':
        data = JSONParser().parse(request)
        time_series_service = TimeSeriesService()
        time_series_service.update_series_batch(data)
        return Response(status=status.HTTP_200_OK, data='OK')

