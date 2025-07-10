from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Store, Order, Product, Delivery, StoreFollow, Status
from .serializers import StoreSerializer, OrderSerializer, ProductSerializer, DeliverySerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.throttling import AnonRateThrottle
from django.db.models import Prefetch
from rest_framework import status
from django.db.models import Count
from .permissions import IsProductOwner, IsStoreOwner
from django.contrib.auth import get_user_model
from .serializers import StoreFollowSerializer, UserSerializer, DashboardSerializer, StatusSerializer
from .models import Status
from django.shortcuts import get_object_or_404
from django.utils import timezone
import json
from .tasks import upload_status_files
from base64 import b64encode
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from logistics.utils.get_riders import get_nearby_drivers
from logistics.utils.eta import get_eta_distance_and_fare
from .utils.get_store_cordinate import get_coordinates_from_address


User = get_user_model()


class CustomAnonRateThrottle(AnonRateThrottle):
    rate = '5/minute'  # Limit to 5 requests per minute


class StoreListCreateView(generics.ListCreateAPIView):
    queryset = store_qs = Store.objects.prefetch_related(
        Prefetch(
            'statuses',
            queryset=Status.objects.filter(expires_at__gt=timezone.now())
        )
    )
    serializer_class = StoreSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]


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
        store = self.request.user.store
        status = self.request.GET.get('status', 'New_Orders')
        return Order.objects.filter(store=store, status=status)


class OrderDetailView(generics.RetrieveDestroyAPIView):
    throttle_classes = [CustomAnonRateThrottle]
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


class GetUserOrder(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]
    
    
    def get(self, request):
        try:
            print(request.user.username)
            orders = Order.objects.filter(buyer=request.user)
            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data, status=200)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_204_NO_CONTENT)


class ConfirmOrder(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def post(self, request, pk):
        try:
            order = get_object_or_404(Order, order_id=pk)
            order.status = 'processing'
            order.save()
            print(order.order_id)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"order_{order.order_id}",
                {
                    "type": "order_status_update",
                    "order_id": order.order_id,
                    "status": order.status,
                }
            )
            return Response({"Message": "Order is being Processed"}, status=200)
            # else:
            #     return Response({"Message": "Order is not a new One"})
           
        except Exception as e:
            return Response(str(e), status=400)
        
        
        
class MarkForDeliveryView(APIView):
    def post(self, request, pk):
        order = get_object_or_404(Order, order_id=pk)
        print(order.delivery)
        delivery_cordinates = get_coordinates_from_address(order.delivery.delivery_address)
        destination = (delivery_cordinates.get('latitude'), delivery_cordinates.get('longitude'))
        origin = (order.store.latitude, order.store.longitude)
        summary = get_eta_distance_and_fare(origin, destination)
        print(summary)
        if order.status != "processing":
            return Response({"error": "Order hasn't been accepted or picked by rider."}, status=400)

        # Get nearby riders (5km range)
        riders = get_nearby_drivers(order.store.latitude, order.store.longitude, radius_km=5)
        
        
        print(riders)
        # # Send FCM/WebSocket notification to each nearby rider
        # for rider in riders:
        #     notify_rider(rider, order)

        return Response({"message": "Riders notified."}, status=200)



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
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]


class UserProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
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
                Prefetch('products'),
                Prefetch(
                    'statuses',
                    queryset=Status.objects.filter(
                        expires_at__gt=timezone.now())
                )
            ).annotate(
                product_count=Count('products'),
                order_count=Count('order'),
                following_count=Count('following_set'),
                followers_count=Count('following_set')).get(owner=user)
            print(store)
            serializer = DashboardSerializer(store)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_404_NOT_FOUND)


class StoreDetailView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        store = get_object_or_404(Store, id=pk)
        serializer = StoreSerializer(store)
        return Response(serializer.data, status=status.HTTP_200_OK)


# <QueryDict: {'content': ['Vvbbb', 'Vvvbb'], 'images': [ < InMemoryUploadedFile: ec05f851-464d-42ec-bcf8-bc56dba8f52a.jpeg (image/jpeg) > , < InMemoryUploadedFile: 38c18e0d-6693-4683-9dfa-f492153e98b8.jpeg (image/jpeg) > ]} >


class StatusView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        store = request.user.store
        if not store:
            return Response({"message": "User has no Store"}, status=status.HTTP_400_BAD_REQUEST)

        contents = request.POST.getlist('content')
        images = request.FILES.getlist('images')
        statuses = []
        if len(contents) != len(images):
            return Response(
                {"error": "The number of captions and images must be the same."},
                status=400
            )

        statuses = []
        for caption, image in zip(contents, images):
            status_obj = Status.objects.create(
                store=store,
                content=caption,
            )
            statuses.append(status_obj)
            file_bytes = b64encode(image.read()).decode('utf-8')
            # file_bytes = image.read()
            upload_status_files.delay(status_obj.id, file_bytes)
        serializer = StatusSerializer(
            statuses, many=True, context={'request': request})
        return Response(serializer.data, status=201)


class ProductStatusView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        product = get_object_or_404(Product, id=pk)
        try:
            storestatus = Status.objects.get(product=product)
            return Response({"message": "Status already exists"}, status=status.HTTP_409_CONFLICT)
        except Status.DoesNotExist:
            images = product.product_images.all()
            if not images.exists():
                return Response({"error": "No image found for this product"}, status=status.HTTP_400_BAD_REQUEST)

            image = images[0]
            print(image)
            try:
                storestatus = Status.objects.create(
                    product=product,
                    store=product.store,
                    image=image.image,
                    content=product.description
                )
            except Exception as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
            serializer = StatusSerializer(storestatus)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, pk):
        store = get_object_or_404(Store, id=pk)
        status_instances = store.statuses.all()
        print(status)
        serializer = StatusSerializer(status_instances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
