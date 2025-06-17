from django.shortcuts import render
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from .serializers import ChatBoxSerializer, MessageSerializer
from .models import ChatBox

# Create your views here.


class ChatBoxView(generics.ListCreateAPIView):
    queryset = ChatBox.objects.all()
    serializer_class = ChatBoxSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    
    
class MessageView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    
    