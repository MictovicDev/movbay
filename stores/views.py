from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Store, Order, Product, Delivery
from .serializers import StoreSerializer, OrderSerializer, ProductSerializer, DeliverySerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.throttling import AnonRateThrottle
from django.db.models import Prefetch
from rest_framework import status
from django.db.models import Count
from .permissions import IsProductOwner



class CustomAnonRateThrottle(AnonRateThrottle):
    rate = '5/minute'  # Limit to 5 requests per minute




class StoreListCreateView(generics.ListCreateAPIView):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    
    
class StoreDetailView(APIView):
    """
    View to list all users in the system.

    * Requires token authentication.
    * Only admin users are able to access this view.
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsProductOwner, permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        pass
        # try:
        #     if request.user.store:
        #         Store.objects.get(owner=request.user)
        #         s
        # return Response(usernames)
    
    
class DeliveryDetailsCreateView(generics.CreateAPIView):
    serializer_class = DeliverySerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    

    def get_queryset(self):
        return Delivery.objects.all()

    def get(self, request):
        try:
            delivery = Delivery.objects.get(user=request.user)
            serializer = self.get_serializer(delivery)
            return Response(serializer.data)
        except Exception as e:
            return Response({"Message": {str(e)}})
    
    
class OrderListCreateView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    
    
    def get_queryset(self):
        user = self.request.user
        status = self.request.GET.get('status', 'New_Orders')
        return Order.objects.filter(user=user, status=status)
        
    
    
class OrderDetailView(generics.RetrieveDestroyAPIView):
    throttle_classes = [CustomAnonRateThrottle]
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    
    
              
class ProductListCreateView(generics.ListCreateAPIView):
    throttle_classes = [CustomAnonRateThrottle]
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Product.objects.select_related('store').prefetch_related('store__owner').all()
    
    
class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    throttle_classes = [CustomAnonRateThrottle]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsProductOwner, permissions.IsAuthenticated]
    
    
    
class UserProductListView(generics.ListAPIView):
    throttle_classes = [CustomAnonRateThrottle]
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]  # login required

    def get_queryset(self):
        user = self.request.user
        return Product.objects.filter(store__owner=user)
    
    
class DashBoardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    def get(self, request):
        try:
            user = request.user
            store = Store.objects.select_related('owner').prefetch_related(
                Prefetch('products')
            ).annotate(
                product_count=Count('products'),
                order_count=Count('orders'),
                followers_count=Count('store_followers')
            ).get(owner=user)
            serializer = StoreSerializer(store)
        except Exception as e:
            return Response({"message": {"User has no store"}}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    