import asyncio
from http.client import HTTPException
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import JSONParser

from LLMEngine.Rag import get_rag_instance

rag = get_rag_instance()
@api_view(['POST'])
def query_endpoint(request):
    if request.method == "POST":
        try:
            post_data = JSONParser().parse(request)

            prompt = post_data['prompt']
            result = rag.answer_to_question(prompt)
            return Response(result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
