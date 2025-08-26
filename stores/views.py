from rest_framework.pagination import PageNumberPagination
from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Store, Order, Product, Delivery, StoreFollow, Status, OrderTracking, ProductRating
from .serializers import StoreSerializer, OrderSerializer, ProductSerializer, DeliverySerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.throttling import AnonRateThrottle
from django.db.models import Prefetch
from rest_framework import status
from django.db.models import Count
from .permissions import IsProductOwner, IsStoreOwner
from django.contrib.auth import get_user_model
from .serializers import (StoreFollowSerializer,
                          UserSerializer,
                          DashboardSerializer,
                          StatusSerializer,
                          OrderTrackingSerializer,
                          StoreUpdateSerializer,
                          ReviewSerializer,
                          UpdateProductSerializer,
                          ProductRatingSerializer)
from .models import Status
from django.shortcuts import get_object_or_404
from django.utils import timezone
import json
import datetime
from .tasks import upload_status_files, send_push_notification, upload_store_files
from base64 import b64encode
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from logistics.utils.get_riders import get_nearby_drivers
from logistics.utils.eta import get_eta_distance_and_fare
from .utils.get_store_cordinate import get_coordinates_from_address
from django.db import transaction
from .models import Review
from users.models import RiderProfile
from logistics.models import Ride
from users.utils.otp import OTPManager
from .tasks import send_order_complete_email_async, handle_speedy_dispatch_task
from django.template.loader import render_to_string
from .serializers import VerifyOrderSerializer, ClientStoreSerializer
from django.shortcuts import get_object_or_404, get_list_or_404
from stores.utils.calculate_order_package import calculate_order_package
from logistics.service import SpeedyDispatch
# from .utils.create_speedy_dispatch import handle_speedy_dispatch
from logistics.models import Address

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
import logging
from wallet.models import Wallet

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomAnonRateThrottle(AnonRateThrottle):
    rate = '5/minute'  # Limit to 5 requests per minute


class ClientViewStore(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def get(self, request, store_id):
        try:
            store = Store.objects.prefetch_related('products').get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=404)

        serializer = ClientStoreSerializer(store, context={'request': request})
        return Response(serializer.data)


class StoreListCreateView(generics.ListCreateAPIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    try:
        queryset = store_qs = Store.objects.prefetch_related(
            Prefetch(
                'statuses',
                queryset=Status.objects.filter(expires_at__gt=timezone.now())
            )
        )
        serializer_class = StoreSerializer
    except Exception as e:
        print(e)


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


class MarkAsDelivered(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # if request.user.user_type=='Rider':
        #     return Response({"message":"Rider cannot mark an Order as Delivered"})
        order = get_object_or_404(Order, order_id=pk)
        otp_manager = OTPManager()
        secret = otp_manager.get_secret()
        buyer = order.buyer
        otp = otp_manager.generate_otp()
        print(otp)
        order.otp_secret = secret
        html_content = render_to_string(
            'emails/ordercomplete.html', {'user': buyer.username, 'order_otp': otp})
        print(html_content)
        print(buyer.email)
        send_order_complete_email_async.delay(from_email='noreply@movbay.com',
                                              to_emails=buyer.email,
                                              subject='Order Verification',
                                              html_content=html_content)
        order.status = 'completed'
        order.completed = True
        order.order_tracking.all()[0].completed = True
        order.save()
        return Response({"message": "Order has been Completed"}, status=200)


class ConfirmOrder(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # Debug 1
        print(f"DEBUG: ConfirmOrder POST request received for pk: {pk}")

        try:
            with transaction.atomic():
                # Lock the row to prevent concurrent updates
                order = Order.objects.select_for_update().get(order_id=pk)
                if order.status == 'processing':
                    # Debug 3a
                    print("DEBUG: Order already processing, returning bad request.")
                    return Response({"Message": "Order is already being processed."}, status=status.HTTP_400_BAD_REQUEST)

                order.status = 'processing'
                order.save()
                # You could use transaction.on_commit here to trigger the push only after DB is committed
                data = 'Your Order has been confirmed, start tracking it.'

                transaction.on_commit(lambda: send_push_notification.delay(
                    token=order.buyer.device.all()[0].token,
                    title='Your Order has been Confirmed',
                    notification_type="Order Confirmation",
                    data=data
                ))

            return Response({"Message": "Order is being Processed"}, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({"Message": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            print(f"DEBUG: An exception occurred: {e}")  # Debug 6
            return Response({"Message": f"Something went wrong - {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrackOrder(APIView):
    serializer_class = OrderTrackingSerializer

    def get(self, request, pk):
        try:
            order = get_object_or_404(Order, order_id=pk)
            order_tracking = order.order_tracking.all()[0]
            serializer = OrderTrackingSerializer(order_tracking)
            return Response(serializer.data, status=200)
        except Exception as e:
            logger.info("Error Occured During Product Tracking")
            return Response({"Message": "Error Tracking Order"}, status=400)


class MarkForDeliveryView(APIView):
    def post(self, request, pk):

        def notify_drivers(drivers, summary):
            try:
                for driver in drivers:
                    device_token = driver.get('driver').device.all()[0].token
                    logger.info(device_token)
                    if device_token:
                        try:
                            send_push_notification.delay(
                                token=device_token,
                                title='New Ride Alert on movbay',
                                notification_type="Ride Alert",
                                data='You have a new ride suggestion on Movbay, check it out and start earning')
                        except Exception as e:
                            print(str(e))
                            return Response(str(e), status=400)
            except Exception as e:
                return Response({"message": f"Error occured -- {str(e)}"}, status=400)

        with transaction.atomic():
            order = get_object_or_404(Order, order_id=pk)
            order_tracking, _ = OrderTracking.objects.get_or_create(
                order=order)
            delivery_method = order.delivery.delivery_method
            if order.status != "processing":
                return Response({"error": "Order has not been accepted yet."}, status=400)

            if delivery_method == 'MovBay_Dispatch':
                try:
                    delivery_cordinates = get_coordinates_from_address(
                        order.delivery.delivery_address)
                    if delivery_cordinates:
                        destination = (delivery_cordinates.get('latitude'),
                                       delivery_cordinates.get('longitude'))
                    # print(destination)
                    store_cordinates = get_coordinates_from_address(
                        order.store.address1)
                    origin = (store_cordinates.get('latitude'),
                              store_cordinates.get('longitude'))
                    # print(origin)
                    summary = get_eta_distance_and_fare(origin, destination)
                    # print(summary)
                    riders = get_nearby_drivers(store_cordinates.get(
                        'latitude'), store_cordinates.get('longitude'), radius_km=5)
                    # print(riders)
                    order.assigned = True
                    order.save()
                    transaction.on_commit(
                        lambda: notify_drivers(riders, summary))
                    ride = Ride.objects.create(
                        latitude=origin[0], longitude=origin[1], order=order, **summary)
                    return Response({"message": "Request Sent Waiting for Riders to accept"}, status=200)
                except Exception as e:
                    return Response({"error": str(e)}, status=200)

            elif delivery_method == 'Speedy_Dispatch':

                pass
                # handle_speedy_dispatch(order)

                # payload = calculate_order_package(order_items)
                # result = dispatch.create_pickupaddress(order=order)
                # result6 = dispatch.create_deliveryaddress(order=order)
                # result2 = dispatch.create_package(payload)
                # result3 = dispatch.create_parcel(order, payload.get(
                #     'weight'), result2.get('data')['packaging_id'])
                # result4 = dispatch.get_shipping_rates(result.get('data')['address_id'], result6.get('data')['address_id'], result3.get('data')['parcel_id'])


class CustomProductPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'page_size'
    max_page_size = 50


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    pagination_class = CustomProductPagination
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
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]

    def post(self, request, pk):
        try:
            store = Store.objects.get(id=pk)
        except Store.DoesNotExist:
            return Response({"Message": "User Does not Exist"}, status=status.HTTP_404_NOT_FOUND)
        try:
            profile = request.user.user_profile
            store_follow, created = StoreFollow.objects.get_or_create(
                follower=profile, followed_store=store)
        except Exception as e:
            print(str(e))
        serializer = StoreFollowSerializer(store_follow)
        return Response({
            "message": "Follow Successful",
            "data": serializer.data
        }, status=200)


class StoreFollowers(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.db.models import Exists, OuterRef

        try:
            profile = request.user.user_profile
            my_store = Store.objects.get(owner=request.user)
        except Store.DoesNotExist:
            return Response({"message": "You don't own a store"}, status=404)

        followers = (
            StoreFollow.objects
            .filter(followed_store=my_store)
            .select_related("follower__user")   # ✅ ensures serializer has data
        )

        follow_back_qs = StoreFollow.objects.filter(
            follower=profile,
            followed_store__owner__profile=OuterRef(
                "follower")  # compare profile to profile
        )

        followers = (
            StoreFollow.objects
            .filter(followed_store=my_store)
            .annotate(
                is_followed_back=Exists(follow_back_qs)
            )
            .select_related("follower__user")
        )

        serializer = StoreFollowSerializer(followers, many=True)
        return Response(serializer.data, status=200)


class StoreUnfollowView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            store = Store.objects.get(id=pk)
        except Store.DoesNotExist:
            return Response({"Message": "Store Does not Exist"}, status=status.HTTP_404_NOT_FOUND)
        try:
            profile = request.user.user_profile
            store_follow = StoreFollow.objects.get(
                followed_store=store, follower=profile)
            store_follow.delete()
        except Exception as e:
            return Response(str(e), status=400)
        try:
            serializer = StoreFollowSerializer(store_follow)
        except Exception as e:
            return Response(str(e), status=400)
        return Response({
            "message": "UnFollow Successful",
            "data": serializer.data
        }, status=200)


# class StoreFollowing(APIView):
#     authentication_classes = [JWTAuthentication, SessionAuthentication]
#     permission_classes = [permissions.IsAuthenticated]

#     def get(self, request):
#         store = get_object_or_404(Store, owner=request.user)
#         #storefollow = get_list_or_404(StoreFollow.objects.filter(following=store))
#         try:
#             storefollow = StoreFollow.objects.filter(following=store, follow=True)
#             serializer = StoreFollowSerializer(storefollow, many=True)
#         except Exception as e:
#             print(str(e))
#         return Response(serializer.data, status=200)


class StoreFollowingView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.db.models import Exists, OuterRef
        try:
            profile = request.user.user_profile  # ✅ get UserProfile of current user

            # all stores this profile is following
            following = (
                StoreFollow.objects
                .filter(follower=profile)
                # load related
                .select_related('followed_store', 'followed_store__owner')
            )

            # subquery: check if that store owner also follows me back
            they_follow_back_qs = StoreFollow.objects.filter(
                follower=OuterRef('followed_store__owner__user_profile'),
                followed_store__owner=profile.user
            )

            # annotate boolean field
            following = following.annotate(
                they_follow_me_back=Exists(they_follow_back_qs))

            serializer = StoreFollowSerializer(following, many=True)
            return Response(serializer.data, status=200)

        except Exception as e:
            return Response(str(e), status=400)


class UserProductListView(generics.ListAPIView):
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
            store = Store.objects \
                .select_related('owner') \
                .prefetch_related(
                    Prefetch('products'),
                    Prefetch(
                        'statuses',
                        queryset=Status.objects.filter(
                            expires_at__gt=timezone.now())
                    )
                ) \
                .annotate(
                    product_count=Count('products', distinct=True),
                    order_count=Count('order', distinct=True),
                    following_count=Count(
                        'owner__user_profile__follows', distinct=True),
                    # since related_name="followers"
                    followers_count=Count('store_followers', distinct=True),
                ) \
                .get(owner=user)

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

    def put(self, request, pk):
        try:
            store = Store.objects.get(pk=pk)

            if store.owner != request.user:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

            serializer = StoreUpdateSerializer(store, data=request.data)
            serializer.is_valid(raise_exception=True)

            # Extract and read files
            file_data = {}

            if 'cac' in request.FILES:
                file_data['cac'] = request.FILES['cac'].read()
            if 'nin' in request.FILES:
                file_data['nin'] = request.FILES['nin'].read()
            if 'store_image' in request.FILES:
                file_data['store_image'] = request.FILES['store_image'].read()
            serializer.save()  # Save textual fields and others

            # Send files to Celery task for upload if any exist
            if file_data:
                upload_store_files.delay(store.id, file_data)
            return Response({'message': 'Store updated successfully', 'data': serializer.data}, status=status.HTTP_200_OK)

        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        try:
            store = Store.objects.get(pk=pk)

            if store.owner != request.user:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

            serializer = StoreUpdateSerializer(
                store, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            # Extract and read files
            file_data = {}
            if 'cac' in request.FILES:
                file_data['cac'] = request.FILES['cac'].read()
            if 'nin' in request.FILES:
                file_data['nin'] = request.FILES['nin'].read()
            if 'store_image' in request.FILES:
                file_data['store_image'] = request.FILES['store_image'].read()

            serializer.save()

            if file_data:
                upload_store_files.delay(store.id, file_data)

            return Response({'message': 'Store partially updated', 'data': serializer.data}, status=status.HTTP_200_OK)

        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReviewView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id)
            reviews = Review.objects.filter(store=store)
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id)
            print(store)
            serializer = ReviewSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user, store=store)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MoreFromSeller(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        product = get_object_or_404(Product, id=pk)
        store = request.user.store
        product = Product.objects.filter(
            store=store).exclude(id=product.id)[:4]


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


class VerifyOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    """
    Endpoint Used to Verify the completion of an Order, Either By a Seller or a Rider
    """

    def post(self, request, pk):
        serializer = VerifyOrderSerializer(data={'otp': request.data['otp']})
        if serializer.is_valid():
            try:
                order = get_object_or_404(Order, order_id=pk)
                if order.completed == True:
                    return Response({"message": "Order Already Completed Succesfully"}, status=200)
                otp = serializer.validated_data['otp']
                ride = order.ride.all()
                order_secret = order.otp_secret
                if request.user.user_type == 'User' and request.user == order.store.owner:
                    if ride:
                        if not ride[0].completed:
                            return Response({"message": "Ride is Ongoing"})
                    if OTPManager(order_secret).verify_otp(otp):
                        order.completed = True
                        order_tracking = get_object_or_404(
                            OrderTracking, order=order)
                        order_tracking.completed = True
                        order_tracking.save()
                        print(order.store.owner.wallet.balance)
                        owner = order.store.owner
                        wallet = get_object_or_404(Wallet, owner=owner)
                        admin_wallet = get_object_or_404(Wallet, owner__email='admin@mail.com')
                        admin_wallet.balance -= order.amount
                        wallet.balance += order.amount
                        admin_wallet.save()
                        wallet.save()
                        order.save()
                        return Response({"message": "Order Completed Succesfully"}, status=200)
                    else:
                        return Response({'message': 'Invalid or expired OTP'}, status=400)
                elif request.user.user_type == 'Rider' and request.user == ride[0].rider:
                    if OTPManager(order_secret).verify_otp(otp):
                        try:
                            ride = get_object_or_404(Ride, order=order)
                            order_tracking = get_object_or_404(
                                OrderTracking, order=order)
                            ride.completed = True
                            order_tracking.completed = True
                            order_tracking.save()
                            ride.save()
                        except Exception as e:
                            print(str(e))
                        return Response({"message": "Ride Completed Succesfully"}, status=200)
                    else:
                        return Response({'message': 'Invalid or expired OTP'}, status=400)
            except Order.DoesNotExist:
                return Response({'message': 'Order not found'}, status=404)


class MoreFromSeller(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)

        # Main product details
        product_data = ProductSerializer(product).data
        print(product_data)
        # More from seller
        more_from_seller = Product.objects.filter(
            store=product.store
        ).exclude(id=product.id)[:4]
        more_from_seller_data = ProductSerializer(
            more_from_seller, many=True).data

        # Related products by categories
        related_products = Product.objects.filter(
            category=product.category
        ).exclude(id=product.id).distinct()[:4]
        related_products_data = ProductSerializer(
            related_products, many=True).data

        return Response({
            'product': product_data.get('id'),
            'more_from_seller': more_from_seller_data,
            'related_products': related_products_data
        }, status=status.HTTP_200_OK)


class ProductRatingView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """Retrieve all ratings for a given product."""
        product = get_object_or_404(Product, id=pk)
        ratings = ProductRating.objects.filter(product=product)
        serializer = ProductRatingSerializer(ratings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        product = get_object_or_404(Product, id=pk)
        print("Raw request data:", request.data)

        serializer = ProductRatingSerializer(data=request.data)
        print("Serializer is valid:", serializer.is_valid())
        print("Serializer errors:", serializer.errors)
        print("Serializer validated data:", serializer.validated_data)

        if serializer.is_valid():
            ProductRating.objects.create(
                **serializer.validated_data,
                product=product,
                user=request.user
            )
            return Response(
                {"detail": "Rating submitted successfully."},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



{
  "delivery_details": {
    "fullname": "John Doe",
    "phone_number": "+2348012345678",
    "email_address": "johndoe@example.com",
    "country": "NG",
    "city": "Lagos",
    "state": "Lagos",
    "delivery_address": "12 Admiralty Way, Lekki",
    "alternative_address": "Block B, Flat 2"
  },
  "items": [
    {
      "amount": 49000,
      "product": 2,
      "store": 2,
      "quantity": 1
    },
    {
      "amount": 9900,
      "product": 2,
      "quantity": 1,
      "store": 2
    }
  ]
}


class GetShippingRate(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        per_kg = 200
        delivery_details = request.data.get('delivery_details')
        order_items = request.data.get('items')
        
        delivery_cordinates = get_coordinates_from_address(
            delivery_details.get('delivery_address')
        )
        print(delivery_cordinates)
        if delivery_cordinates:
            destination = (
                delivery_cordinates.get('latitude'),
                delivery_cordinates.get('longitude')
            )
       
        # package weight cost
        package_details = calculate_order_package(order_items=order_items)
        weight_cost = package_details.get('weight') * per_kg

        delivery_price = []
        # track stores so you only charge once per store
        unique_store_ids = set()
        
        for item in order_items:
            store_id = item.get('store')
            if store_id not in unique_store_ids:  
                unique_store_ids.add(store_id)

                store = get_object_or_404(Store, id=store_id)
                store_cordinates = get_coordinates_from_address(store.address1)
                origin = (
                    store_cordinates.get('latitude'),
                    store_cordinates.get('longitude')
                )
                
                summary = get_eta_distance_and_fare(origin, destination)
                delivery_price.append(summary.get('fare_amount'))
        print(delivery_price)

        # total cost = fares for each unique store + weight cost
        delivery_cost = sum(delivery_price) + weight_cost +300
        
        return Response(delivery_cost, status=200)

               

class GetShipMentRate(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, product_id):
        user = request.user
        # product_id = request.data.get('product_id')
        delivery_details = request.data.get('delivery_details')
        order_items = request.data.get('items')
        # Trigger the Celery task
        task = handle_speedy_dispatch_task.delay(
            user_id=user.id,
            product_id=product_id,
            delivery_details=delivery_details,
            order_items_data=order_items
        )

        return Response({
            "status": "success",
            "message": "Shipping rate processing started",
            "task_id": task.id
        }, status=status.HTTP_202_ACCEPTED)
        # handle_speedy_dispatch(user, product_id, delivery_details, order_items)


class TaskStatusView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    """API endpoint to check the status of a Celery task via GET request.

    Args:
        task_id: The ID of the Celery task to check.
    """

    def get(self, request, task_id):
        """Handle GET request to check Celery task status.

        Args:
            request: The HTTP request object.
            task_id: The ID of the Celery task (from URL).

        Returns:
            Response: JSON response with task status, result, or error.
        """
        try:
            # Ensure user is authenticated
            # if not request.user.is_authenticated:
            #     logger.warning("Unauthorized attempt to check task %s", task_id)
            #     return Response(
            #         {
            #             "status": "error",
            #             "message": "Authentication required",
            #             "error": "User must be logged in"
            #         },
            #         status=status.HTTP_401_UNAUTHORIZED
            #     )

            # Get task result
            task_result = AsyncResult(task_id)
            if not task_result:
                logger.error("Invalid task_id: %s", task_id)
                return Response(
                    {
                        "status": "error",
                        "message": "Invalid task ID",
                        "error": "Task not found"
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if the task belongs to the user
            task_args = task_result.args or ()  # Get task arguments
            # if not task_args or task_args[0] != request.user.id:
            #     logger.warning("User %s attempted to access unauthorized task %s", request.user.id, task_id)
            #     return Response(
            #         {
            #             "status": "error",
            #             "message": "Unauthorized",
            #             "error": "You do not have permission to access this task"
            #         },
            #         status=status.HTTP_403_FORBIDDEN
            #     )

            # Check task status
            if task_result.ready():
                if task_result.successful():
                    logger.info(
                        "Task %s completed successfully for user %s", task_id, request.user.id)
                    return Response(
                        {
                            "status": "success",
                            "message": "Task completed successfully",
                            "data": task_result.result
                        },
                        status=status.HTTP_200_OK
                    )
                else:
                    error_message = str(
                        task_result.result) if task_result.result else "Unknown task error"
                    logger.error("Task %s failed for user %s: %s",
                                 task_id, request.user.id, error_message)
                    return Response(
                        {
                            "status": "error",
                            "message": "Task failed",
                            "error": error_message
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                logger.info("Task %s is still processing for user %s",
                            task_id, request.user.id)
                return Response(
                    {
                        "status": "pending",
                        "message": "Task is still processing",
                        "data": None
                    },
                    status=status.HTTP_202_ACCEPTED
                )

        except Exception as e:
            logger.critical("Unexpected error checking task %s for user %s: %s",
                            task_id, request.user.id, str(e), exc_info=True)
            return Response(
                {
                    "status": "error",
                    "message": "Internal server error",
                    "error": "An unexpected error occurred"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
