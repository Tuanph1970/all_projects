from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from repositories.file_management_repository import FileUploadRepository
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.conf import settings
@api_view(['GET'])
def get_upload_files(request):
    if request.method == 'GET':
        file_repo = FileUploadRepository()
        data = file_repo.get_upload_files()
        return Response(data)

@api_view(['POST'])
def delete_upload_file(request):
    if request.method == 'POST':
        post_data = JSONParser().parse(request)
        file_id = post_data['id']
        file_repo = FileUploadRepository()
        file_repo.delete_file(file_id)
        file_name = file_repo.get_file_name_by_id(file_id)
        return Response({
            "status": "success",
            "message": "File removed successfully",
        })
@csrf_exempt
@api_view(['POST'])
def insert_file(request):
    if request.method == 'POST':
        try:
            # Check if file was uploaded
            if 'file' not in request.FILES:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No file provided'
                }, status=400)

            uploaded_file = request.FILES['file']

            # Define destination path
            DESTINATION = getattr(settings, 'FILE_UPLOAD_DESTINATION', 'uploads')
            fullpath = os.path.join(DESTINATION, uploaded_file.name)
            path_data = os.path.join(os.getcwd(), "data")

            # Set permissions
            os.makedirs(path_data, exist_ok=True)
            os.chmod(path_data, 0o0777)

            # Save file using Django's default storage
            file_path = default_storage.save(fullpath, uploaded_file)

            # Call your insert function (assuming it exists)
            file_repo = FileUploadRepository()
            file_repo.insert_file(uploaded_file.name)

            return JsonResponse({
                'status': 'success',
                'message': 'save file success'
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

