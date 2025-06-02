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




class StoreListCreateView(generics.ListCreateAPIView):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    
    
    
class OrderListCreateView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    
    
class OrderDetailView(generics.RetrieveDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    
     
class ConfirmOrderView(APIView):
    pass
    
class DashBoardView(APIView):
    pass
    
class CancelOrderView(APIView):
    def delete(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            if order.status == 'CANCELLED':
                return Response({'detail': 'Order already cancelled.'}, status=400)
            order.status = 'CANCELLED'
            order.save()
            return Response({'detail': 'Order cancelled successfully.'}, status=200)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=404)
        
        
        
class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    
    
class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    
    
class DeleteProductView(generics.DestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    
    