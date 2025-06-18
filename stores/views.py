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
from .models import StoreFollow
from django.contrib.auth import get_user_model
from .serializers import StoreFollowSerializer, UserSerializer

User = get_user_model()

class CustomAnonRateThrottle(AnonRateThrottle):
    rate = '5/minute'  # Limit to 5 requests per minute




class StoreListCreateView(generics.ListCreateAPIView):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    
    
    
    
# class StoreDetailView(APIView):
#     """
#     View to list all users in the system.

#     * Requires token authentication.
#     * Only admin users are able to access this view.
#     """
#     authentication_classes = [JWTAuthentication, SessionAuthentication]
#     permission_classes = [IsProductOwner, permissions.IsAuthenticated]
    
#     def get(self, request, format=None):
#         pass
#         # try:
#         #     if request.user.store:
#         #         Store.objects.get(owner=request.user)
#         #         s
#         # return Response(usernames)
    
    
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
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsProductOwner, permissions.IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    
    
class UserProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsProductOwner, permissions.IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]

 
class StoreFollowView(APIView):
    permission_classes = [IsProductOwner, permissions.IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    
    
    def post(self, request, pk):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response({"Message": "User Does not Exit"}, status=status.HTTP_404_NOT_FOUND)
        store_follow, created = StoreFollow.objects.get_or_create(
            follower=user,  # the person being followed
            following=request.user  # the person following
        )
        serializer = StoreFollowSerializer(store_follow)
        return Response({
            "message": "Follow Successful",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
        
        
        
class StoreFollowers(APIView):
    def get(self, request):
        user = request.user
        followers = user.followers_set.select_related('follower')
        users = [follow.follower for follow in followers]
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    
    
    

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
            return Response([], status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    