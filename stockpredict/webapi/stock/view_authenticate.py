from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from repositories.authentication_repository import AuthenticationRepository
import jwt
import datetime


@api_view(['POST'])
def login(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        auth_repo = AuthenticationRepository()
        ret = auth_repo.login(data['user_email'], data['user_password'])

        if ret['id'] != -1:
            payload = {
                'user_id': ret['id'],
                'email': data['user_email'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }
            token = jwt.encode(payload, 'secret_key', algorithm='HS256')
            return Response({'token': token, 'user_id': ret['id']})
        else:
            return Response({'error': 'Invalid credentials'}, status=401)


@api_view(['POST'])
def signup(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        user_name = data["user_name"]
        user_email = data['user_email']
        password = data['password']
        auth_repo = AuthenticationRepository()
        ret = auth_repo.sign_up_new_user(user_name, user_email, password)
        return Response(ret)


@api_view(['POST'])
def change_pass(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        user_name = data["user_email"]
        old_pass = data["current_password"]
        new_pass = data['new_password']
        auth_repo = AuthenticationRepository()
        ret = auth_repo.change_password(user_name, old_pass, new_pass)
        return Response(ret)


@api_view(['POST'])
def reset_pass(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        user_email = data["user_email"]
        auth_repo = AuthenticationRepository()
        ret = auth_repo.reset_password(user_email, new_password="123456")
        return Response(ret)




