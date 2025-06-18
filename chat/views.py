from django.shortcuts import render
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from .serializers import ChatBoxSerializer, MessageSerializer
from .models import ChatBox
from rest_framework import status
from .utils.chatupdate import ChatUpdateHandler
from rest_framework.views import APIView
from rest_framework.response import Response
from channels.db import database_sync_to_async



class ChatBoxAsyncView(APIView):
    async def post(self, request):
        serializer = ChatBoxSerializer(data=request.data)
        if serializer.is_valid():
            instance = await database_sync_to_async(serializer.save)(sender=request.user)

            chat_id = instance.chat_id
            message_data = {
                "sender": instance.sender.username,
                "message": instance.content,
            }

            handler = ChatUpdateHandler()
            await handler.send_chat_update(chat_id, message_data)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
    
    
class MessageView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    
    def perform_create(self, serializer):
        pass

    
    