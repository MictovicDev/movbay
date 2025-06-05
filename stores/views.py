from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Store, Order, Product
from .serializers import StoreSerializer, OrderSerializer, ProductSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import RetrieveDestroyAPIView
from rest_framework.throttling import AnonRateThrottle



class CustomAnonRateThrottle(AnonRateThrottle):
    rate = '5/minute'  # Limit to 5 requests per minute




class StoreListCreateView(generics.ListCreateAPIView):
    throttle_classes = [CustomAnonRateThrottle]
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    
    
    
class OrderListCreateView(generics.ListCreateAPIView):
    throttle_classes = [CustomAnonRateThrottle]
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    
    
class OrderDetailView(generics.RetrieveDestroyAPIView):
    throttle_classes = [CustomAnonRateThrottle]
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    
    
        
    
        
class ProductListCreateView(generics.ListCreateAPIView):
    throttle_classes = [CustomAnonRateThrottle]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    
    
class ProductDetailView(generics.RetrieveAPIView):
    throttle_classes = [CustomAnonRateThrottle]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    
    
class DeleteProductView(generics.DestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    
    