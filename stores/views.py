from rest_framework import permissions, status
from rest_framework import status, permissions
from datetime import datetime, timedelta
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
from .serializers import (
    UserSerializer,
    DashboardSerializer,
    StatusSerializer,
    OrderTrackingSerializer,
    StoreUpdateSerializer,
    ReviewSerializer,
    UpdateProductSerializer,
    ProductRatingSerializer,
    StoreFollowSerializer,
    ProductDeliveryTypeSerializer)
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
from .tasks import send_order_complete_email_async, handle_speedy_dispatch_task, send_receipt_email
from django.template.loader import render_to_string
from .serializers import VerifyOrderSerializer, ClientStoreSerializer
from django.shortcuts import get_object_or_404, get_list_or_404
from stores.utils.calculate_order_package import calculate_order_package
from logistics.service import SpeedyDispatch
# from .utils.create_speedy_dispatch import handle_speedy_dispatch
from logistics.models import Address, PackageDelivery
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult
import logging
from wallet.models import Wallet
from stores.utils.create_speedy_dispatch import handle_speedy_dispatch
from stores.utils.render_to_string import render_to_new_string
from stores.utils.generate_pdf import generate_receipt_pdf
import requests
from logistics.models import ValidateAddress
from datetime import timedelta
from collections import defaultdict
import os
from random import randint
from stores.utils.shipping_request import shipping_request
import base64
from .tasks import upload_single_image, upload_video
from users.serializers import UserProfileSerializer
from rest_framework import serializers


logger = logging.getLogger(__name__)
User = get_user_model()


class CustomAnonRateThrottle(AnonRateThrottle):
    rate = '5/minute'  # Limit to 5 requests per minute


class ClientViewStore(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [JWTAuthentication, SessionAuthentication]

    def get(self, request, store_id):
        try:
            store = Store.objects.prefetch_related('products').get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'Store not found'}, status=404)

        serializer = ClientStoreSerializer(store, context={'request': request})
        return Response(serializer.data)


class StoreListCreateView(generics.ListCreateAPIView):
    # authentication_classes = [JWTAuthentication, SessionAuthentication]
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
    # authentication_classes = [JWTAuthentication, SessionAuthentication]
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
    # authentication_classes = [JWTAuthentication, SessionAuthentication]

    def get_queryset(self):
        store = self.request.user.store
        status = self.request.GET.get('status', 'New_Orders')
        return Order.objects.filter(store=store, status=status)


class OrderDetailView(generics.RetrieveDestroyAPIView):
    throttle_classes = [CustomAnonRateThrottle]
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


class GetUserOrder(APIView):
    # authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def get(self, request):
        try:
            # Get query parameter (defaults to False if not provided)
            complete_param = request.query_params.get(
                "complete", "false").lower()
            if complete_param not in ["true", "false"]:
                return Response({"error": "Invalid value for 'complete'. Use true or false."},
                                status=status.HTTP_400_BAD_REQUEST)

            complete = complete_param == "true"

            # Filter based on query parameter
            orders = Order.objects.filter(
                buyer=request.user, completed=complete)
            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetPastUserOrder(APIView):
    # authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def get(self, request):
        try:
            print(request.user.username)
            orders = Order.objects.filter(buyer=request.user, completed=True)
            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data, status=200)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_204_NO_CONTENT)


class MarkAsDelivered(APIView):
    # authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        d_type = request.query_params.get(
            "type", "order")  # default = order
        if d_type == 'order':
            print('Order Entered')
            order = get_object_or_404(Order, order_id=pk)
            if order.status == 'completed':
                return Response({"message": "Order is already marked as completed"}, status=400)
            buyer = order.buyer
            otp_manager = OTPManager()
            secret = otp_manager.get_secret()
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
            order.order_tracking.all()[0].completed = True
            order.save()
            return Response({"message": "Order has been Completed"}, status=200)

        elif d_type == 'package-delivery':
            print('Package Delivery Entered')
            package_delivery = get_object_or_404(PackageDelivery, id=pk)
            if package_delivery.completed:
                return Response({"message": "Package is already marked as delivered"}, status=400)
            sender = package_delivery.sender
            otp_manager = OTPManager()
            secret = otp_manager.get_secret()
            otp = otp_manager.generate_otp()
            print(otp)
            package_delivery.otp_secret = secret
            html_content = render_to_string(
                'emails/ordercomplete.html', {'user': sender.user.username, 'order_otp': otp})
            print(html_content)
            print(sender.user.email)
            send_order_complete_email_async.delay(from_email='noreply@movbay.com',
                                                  to_emails=sender.user.email,
                                                  subject='Order Verification',
                                                  html_content=html_content)

            return Response({"message": "Package Marked as Delivered"}, status=200)
        else:
            return Response({"message": "Invalid type parameter"}, status=400)


class ConfirmOrder(APIView):
    # authentication_classes = [JWTAuthentication, SessionAuthentication]
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
                print('Yeah Order saving')
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


class CancelOrder(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # Debug 1
        print(f"DEBUG: CancelOrder POST request received for pk: {pk}")

        try:
            with transaction.atomic():
                # Lock the row to prevent concurrent updates
                order = Order.objects.select_for_update().get(order_id=pk)
                if order.store.owner != request.user:
                    # Debug 3a
                    print("DEBUG: You can't Cancel the Order.")
                    return Response({"Message": "You don't have the permission."}, status=status.HTTP_400_BAD_REQUEST)

                order.status = 'cancelled'
                order.save()
                # You could use transaction.on_commit here to trigger the push only after DB is committed
                data = 'Your Order has cancelled.'

                transaction.on_commit(lambda: send_push_notification.delay(
                    token=order.buyer.device.all()[0].token,
                    title='Your Order has been Cancelled',
                    notification_type="Order Cancellation",
                    data=data
                ))

            return Response({"Message": "Order Cancelled Successfully"}, status=status.HTTP_200_OK)

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
            if order.delivery.first().delivery_method == 'ship_bubble':
                print(True)
                url = order.shipment.first().tracking_url
                return Response({"success": True, "type": "ship_bubble", "data": url})
            order_tracking = order.order_tracking.all()[0]
            serializer = OrderTrackingSerializer(order_tracking)
            return Response(serializer.data, status=200)
        except Exception as e:
            logger.info(str(e))
            return Response({"Message": "Error Tracking Order"}, status=400)


def notify_drivers(drivers, summary):
    """Send push notifications to available drivers"""
    errors = []
    try:
        for driver in drivers:
            try:
                devices = driver.get('driver').device.all()
                if devices:
                    device_token = devices[0].token
                    logger.info(
                        f"Sending notification to: {device_token}")
                    send_push_notification.delay(
                        token=device_token,
                        title='New Ride Alert on movbay',
                        notification_type="Ride Alert",
                        data='You have a new ride suggestion on Movbay, check it out and start earning'
                    )
            except Exception as e:
                errors.append(
                    f"Failed to notify driver {driver.get('driver', {}).get('id', 'unknown')}: {str(e)}")
                logger.error(f"Notification error: {str(e)}")

        if errors:
            logger.warning(f"Some notifications failed: {errors}")
    except Exception as e:
        logger.error(f"Critical error in notify_drivers: {str(e)}")
        raise


class MarkForDeliveryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            order = get_object_or_404(Order, order_id=pk)

            if order.status != "processing":
                return Response({"error": "Order has not been accepted yet."}, status=400)

            deliveries = order.delivery.all()
            if not deliveries:
                return Response({"error": "No deliveries found for this order."}, status=400)

            processing_results = []
            with transaction.atomic():
                # order_tracking, _ = OrderTracking.objects.get_or_create(
                #     order=order)
                for delivery in deliveries:
                    try:
                        if delivery.delivery_method == 'movbay':
                            result = self._process_movbay_dispatch(
                                delivery, order)
                            # processing_results.append(result)
                            if result.get('success'):
                                pdf_content = generate_receipt_pdf(
                                    order_data=order, delivery=delivery)
                                html_content = render_to_new_string(
                                    order, delivery)
                                send_receipt_email.delay(
                                    pdf_content_base64=pdf_content,
                                    order_id=order.order_id,
                                    from_email='noreply@movbay.com',
                                    to_emails=[
                                        order.store.owner.email, order.buyer.email],
                                    subject='Product Receipt',
                                    html_content=html_content
                                )
                                processing_results.append({
                                    'success': True,
                                    'delivery_id': delivery.id,
                                })
                            else:
                                processing_results.append({
                                    'success': False,
                                    'delivery_id': delivery.id, })

                        elif delivery.delivery_method == 'ship_bubble':
                            print(True)
                            result = self._process_speedy_dispatch(delivery)
                            html_content = render_to_new_string(
                                order, delivery)
                            if result.get('success'):
                                print('Success')
                                pdf_content = generate_receipt_pdf(
                                    order_data=order, delivery=delivery)
                                html_content = render_to_new_string(
                                    order, delivery)
                                send_receipt_email.delay(
                                    pdf_content_base64=pdf_content,
                                    order_id=order.order_id,
                                    from_email='noreply@movbay.com',
                                    to_emails=[
                                        order.store.owner.email, order.buyer.email],
                                    subject='Product Receipt',
                                    html_content=html_content
                                )
                                order.out_for_delivery = True
                                order.save()
                                processing_results.append({
                                    'success': True,
                                    'delivery_id': delivery.id,
                                    # 'error': f'Unknown delivery method: {delivery.delivery_method}'
                                })
                                # movbay_processed = True
                            else:
                                processing_results.append({
                                    'success': False,
                                    'delivery_id': delivery.id, })
                        else:
                            processing_results.append({
                                'success': False,
                                'delivery_id': delivery.id,
                                'error': f'Unknown delivery method: {delivery.delivery_method}'
                            })

                    except Exception as e:
                        return Response({"error": str(e)}, status=500)
            return Response(processing_results, status=200)

        except Exception as e:
            logger.error(f"Critical error in MarkForDeliveryView: {str(e)}")
            return Response({"error": "An unexpected error occurred"}, status=500)

    def _process_movbay_dispatch(self, delivery, order):
        """Process movbay dispatch delivery"""
        try:
            # Get coordinates
            delivery_coords = get_coordinates_from_address(
                delivery.delivery_address)
            if not delivery_coords:
                raise ValueError("Could not get delivery coordinates")

            store_coords = get_coordinates_from_address(order.store.address1)
            if not store_coords:
                raise ValueError("Could not get store coordinates")

            destination = (delivery_coords.get('latitude'),
                           delivery_coords.get('longitude'))
            origin = (store_coords.get('latitude'),
                      store_coords.get('longitude'))

            # Get route summary
            summary = get_eta_distance_and_fare(origin, destination)

            # Find nearby drivers
            riders = get_nearby_drivers(
                store_coords.get('latitude'),
                store_coords.get('longitude'),
                radius_km=5
            )

            # Update order status
            order.assigned = True
            order.save()

            # Create ride
            ride = Ride.objects.create(
                latitude=origin[0],
                longitude=origin[1],
                order=order,
                delivery_type='Order',
                **summary
            )

            # Notify drivers (using transaction.on_commit to ensure it runs after transaction)
            transaction.on_commit(lambda: notify_drivers(riders, summary))

            return {
                'success': True,
                'delivery_id': delivery.id,
                'ride_id': ride.id,
                'drivers_notified': len(riders)
            }

        except Exception as e:
            logger.error(f"Movbay dispatch processing failed: {str(e)}")
            return {
                'success': False,
                'delivery_id': delivery.id,
                'error': str(e)
            }

    def _process_speedy_dispatch(self, delivery):
        """Process speedy dispatch delivery"""
        print('Enterered')
        result = shipping_request(delivery)

        return result


class CustomProductPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'page_size'
    max_page_size = 50


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    # pagination_class = CustomProductPagination
    # authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Product.objects.select_related('store').prefetch_related('store__owner').all()


class ProductDeliveryTypesView(APIView):
    def post(self, request, *args, **kwargs):
        product_ids = request.data.get("product_ids", [])

        if not isinstance(product_ids, list) or not product_ids:
            return Response(
                {"error": "product_ids must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        products = Product.objects.filter(id__in=product_ids)

        if not products.exists():
            return Response(
                {"error": "No products found for given IDs"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Start with all delivery types as True
        delivery_options = {
            "movbay_express": True,
            "speed_dispatch": True,
            "pickup": True
        }

        # Take intersection → keep True only if ALL products support it
        for product in products:
            delivery_options["movbay_express"] &= product.movbay_express
            delivery_options["speed_dispatch"] &= product.speed_dispatch
            delivery_options["pickup"] &= product.pickup

        return Response(
            {
                "products_checked": list(products.values_list("id", flat=True)),
                "available_delivery_types": delivery_options
            },
            status=status.HTTP_200_OK
        )


class DeleteProduct(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)

            # Ensure only the store owner can delete the product

            if product.store.owner != request.user:
                return Response(
                    {"error": "Permission denied"},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Delete the product
            product.delete()
            return Response(
                {"message": "Product deleted successfully"},
                status=status.HTTP_204_NO_CONTENT
            )

        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

class StoreFollowView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]

    def post(self, request, pk):
        try:
            store = Store.objects.get(id=pk)
        except Store.DoesNotExist:
            return Response({"message": "Store does not exist"}, status=status.HTTP_404_NOT_FOUND)

        serializer = StoreFollowSerializer(
            data={'followed_store': store.id},
            context={'request': request}
        )

        if serializer.is_valid():
            try:
                follow = serializer.save()
                store_data = StoreSerializer(store, context={'request': request}).data
                store_data['followed_at'] = follow.followed_at
                return Response({
                    "message": "Followed successfully",
                    "is_following": True,
                    "store": store_data
                }, status=status.HTTP_201_CREATED)
            except serializers.ValidationError as e:
                # Handles the “Unfollowed successfully” case
                return Response({
                    "message": str(e.detail[0]),
                    "is_following": False
                }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class StoreFollowers(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.db.models import Exists, OuterRef

        try:
            profile = request.user.user_profile
            my_store = Store.objects.get(owner=request.user)
        except Store.DoesNotExist:
            return Response({"message": "You don't own a store"}, status=404)

        # Check if I follow them back
        follow_back_qs = StoreFollow.objects.filter(
            follower=profile,
            followed_store__owner__user_profile=OuterRef("follower")
        )

        followers = (
            StoreFollow.objects
            .filter(followed_store=my_store)
            .annotate(is_following_back=Exists(follow_back_qs))
            .select_related("follower__user")
        )

        # Build the followers list
        followers_list = []
        for follow in followers:
            follower_data = UserProfileSerializer(follow.follower).data
            follower_data['followed_at'] = follow.followed_at
            follower_data['is_following_back'] = follow.is_following_back
            followers_list.append(follower_data)

        return Response({
            'store': my_store.id,
            'followers_count': len(followers_list),
            'followers': followers_list
        }, status=200)


class StoreFollowingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.db.models import Exists, OuterRef
        try:
            profile = request.user.user_profile

            # Check if they follow me back
            they_follow_back_qs = StoreFollow.objects.filter(
                follower=OuterRef('followed_store__owner__user_profile'),
                followed_store__owner=profile.user
            )

            following = (
                StoreFollow.objects
                .filter(follower=profile)
                .annotate(they_follow_me_back=Exists(they_follow_back_qs))
                .select_related('followed_store', 'followed_store__owner')
            )

            # Build the following list
            following_list = []
            for follow in following:
                store_data = StoreSerializer(follow.followed_store).data
                store_data['followed_at'] = follow.followed_at
                store_data['they_follow_me_back'] = follow.they_follow_me_back
                following_list.append(store_data)

            return Response({
                'following_count': len(following_list),
                'following': following_list
            }, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=400)


class UpdateProduct(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        try:
            # Get the product
            product = Product.objects.get(pk=pk)

            # Permission check
            if product.store.owner != request.user:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

            # Pass data to serializer
            serializer = UpdateProductSerializer(
                product, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            file_data = {}
            video_data = None

            # Handle multiple image uploads
            if 'images' in request.FILES:
                images = request.FILES.getlist('images')
                for image in images:
                    file_content = base64.b64encode(
                        image.read()).decode('utf-8')
                    image_data = {
                        'file_content': file_content,
                        'filename': image.name,
                        'product_id': product.id
                    }
                    upload_single_image.delay(image_data)

            # Handle product video upload
            if 'product_video' in request.FILES:
                video_file = request.FILES['product_video']
                video_content = base64.b64encode(
                    video_file.read()).decode('utf-8')
                upload_video.delay(video_content, product.id)

            return Response({
                'message': 'Product updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    # authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]  # login required

    def get_queryset(self):
        user = self.request.user
        return Product.objects.filter(store__owner=user)


class DashBoardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [JWTAuthentication, SessionAuthentication]

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
   # authentication_classes = [SessionAuthentication, JWTAuthentication]
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


class HealthCheckView(APIView):
    # authentication_classes = [None]
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        product = Product.objects.all()
        store = Store.objects.all()
        return Response({"Message": "Healthy"}, status=200)


class ReviewView(APIView):
    # authentication_classes = [JWTAuthentication, SessionAuthentication]
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
    2  # authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        product = get_object_or_404(Product, id=pk)
        store = request.user.store
        product = Product.objects.filter(
            store=store).exclude(id=product.id)[:4]


class StatusView(APIView):
    # authentication_classes = [SessionAuthentication, JWTAuthentication]
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
    # authentication_classes = [SessionAuthentication, JWTAuthentication]
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
    # authentication_classes = [JWTAuthentication, SessionAuthentication]

    """
    Endpoint Used to Verify the completion of an Order, Either By a Seller or a Rider
    """

    def post(self, request, pk):
        serializer = VerifyOrderSerializer(data={'otp': request.data['otp']})
        query_param = request.query_params.get(
            "type", "order")  # default = order
        if serializer.is_valid():
            print("Serializer is Valid")
            if query_param == 'order':
                print('Order Processing')
                try:
                    order = get_object_or_404(Order, order_id=pk)
                    if order.completed == True:
                        return Response({"message": "Order Already Completed Succesfully"}, status=200)
                    otp = serializer.validated_data['otp']
                    ride = order.ride.all()
                    order_secret = order.otp_secret
                    if request.user.user_type == 'User' and request.user == order.store.owner:
                        print("Store Owner is trying to complete the order")
                        if ride:
                            if not ride[0].completed:
                                return Response({"message": "Ride is Ongoing"})
                        # if OTPManager(order_secret).verify_otp(otp):
                        try:
                            order_tracking = get_object_or_404(
                                OrderTracking, order=order)
                            order_tracking.completed = True
                            order_tracking.save()
                            order_items = order.order_items.all()
                            free_delivery = [
                                item.product.free_delivery for item in order_items]
                            print(order.delivery.first().shiiping_amount)
                            if True in free_delivery:
                                delivery_fee = order.delivery.first().shiiping_amount
                                wallet = get_object_or_404(
                                    Wallet, owner=order.store.owner)
                                wallet.balance -= delivery_fee
                                wallet.save()
                            admin_wallet = get_object_or_404(
                                Wallet, owner__email='admin@mail.com')
                            owner_wallet = get_object_or_404(
                                Wallet, owner=order.store.owner)
                            # Ensure order.amount is a valid number
                            amount = order.amount or 0
                            print(amount)
                            # print(delivery_fee)
                            admin_wallet.balance -= amount
                            admin_wallet.total_withdrawal += amount
                            admin_wallet.save()

                            owner_wallet.balance += amount
                            owner_wallet.total_deposit += amount
                            owner_wallet.save()

                            print("Owner balance:", owner_wallet.balance)
                            print("Admin balance:", admin_wallet.balance)
                            order.completed = True
                            order.save()
                            return Response({"message": "Order Completed Succesfully"}, status=200)
                        except Exception as e:
                            logger.info(str(e))
                            return Response({"message": "Error Completing Order"}, status=400)
                        # else:
                        #     return Response({'message': 'Invalid or expired OTP'}, status=400)
                    elif request.user.user_type == 'Rider' and request.user == ride[0].rider:
                        logger.info("Rider is trying to complete the ride")
                        if OTPManager(order_secret).verify_otp(otp):
                            print('Yeah Verified OTP')
                            try:
                                ride = get_object_or_404(Ride, order=order)
                                order_tracking = get_object_or_404(
                                    OrderTracking, order=order)
                                if ride.completed:
                                    return Response({"message": "Ride Already Completed Succesfully"}, status=200)
                                # ride.completed = True
                                order_tracking.completed = True
                                order_tracking.save()
                                rider_wallet = get_object_or_404(
                                    Wallet, owner=ride.rider)
                                admin_wallet = get_object_or_404(
                                    Wallet, owner__email='admin@mail.com')
                                owner_wallet = get_object_or_404(
                                    Wallet, owner=order.store.owner)

                                # Ensure order.amount is a valid number
                                amount = ride.fare_amount or 0

                                admin_wallet.balance -= amount
                                admin_wallet.total_withdrawal += amount
                                admin_wallet.save()

                                rider_wallet.balance += amount
                                rider_wallet.total_deposit += amount
                                rider_wallet.save()

                                owner_wallet.balance += order.amount
                                owner_wallet.total_deposit += order.amount
                                owner_wallet.save()
                                print(admin_wallet, rider_wallet, owner_wallet)

                                print("Owner balance:", owner_wallet.balance)
                                print("Admin balance:", admin_wallet.balance)
                                ride.completed = True
                                order.completed = True
                                order.save()
                                ride.save()
                                return Response({"message": "Ride Completed Succesfully"}, status=200)
                            except Exception as e:
                                print(str(e))
                                return Response({"message": str(e)}, status=400)
                        else:
                            return Response({'message': 'Invalid or expired OTP'}, status=400)
                    else:
                        return Response({'message': 'Permission Denied'}, status=403)
                except Order.DoesNotExist:
                    return Response({'message': 'Order not found'}, status=404)
            elif query_param == 'package-delivery':
                print('Entered Package Delivery')
                try:
                    delivery = get_object_or_404(
                        PackageDelivery, id=pk)
                    ride = delivery.package_ride.all()[0]
                    if delivery.completed == True:
                        return Response({"message": "Delivery Already Completed Succesfully"}, status=200)
                    otp = serializer.validated_data['otp']
                    print(otp)
                    delivery_secret = delivery.otp_secret
                    # print(request.user.user_type, delivery.order.store.owner)
                    # print(request.user)
                    if request.user.user_type == 'Rider' and request.user == delivery.package_ride.all()[0].rider:
                        print("Rider Is is trying to complete the Delivery")
                        # if OTPManager(delivery_secret).verify_otp(otp):
                        try:
                            ride.completed = True
                            delivery.completed = True
                            delivery.save()
                            rider_wallet = get_object_or_404(
                                Wallet, owner=ride.rider)
                            admin_wallet = get_object_or_404(
                                Wallet, owner__email='admin@mail.com')
                            amount = ride.fare_amount or 0

                            admin_wallet.balance -= amount
                            admin_wallet.total_withdrawal += amount
                            admin_wallet.save()

                            rider_wallet.balance += amount
                            rider_wallet.total_deposit += amount
                            rider_wallet.save()
                            print("Admin balance:", admin_wallet.balance)
                            ride.completed = True
                            ride.save()
                            delivery.completed = True
                            delivery.save()
                            return Response({"message": "Delivery Completed Succesfully"}, status=200)
                        except Exception as e:
                            logger.info(str(e))
                            return Response({"message": "Error Completing Delivery"}, status=400)
                        # else:
                        #     return Response({'message': 'Invalid or expired OTP'}, status=400)
                    else:
                        return Response({'message': 'Permission Denied'}, status=403)
                except Delivery.DoesNotExist:
                    return Response({'message': 'Delivery not found'}, status=404)


class MoreFromSeller(APIView):
    # authentication_classes = [SessionAuthentication, JWTAuthentication]
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
    # authentication_classes = [SessionAuthentication, JWTAuthentication]
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


logger = logging.getLogger(__name__)


def validate_address(payload):
    url = "https://api.shipbubble.com/v1/shipping/address/validate"
    print('Called')
    API_KEY = os.getenv('API_KEY')
    print(API_KEY)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    try:
        print("Payload being sent:")
        print(json.dumps(payload, indent=4))

        response = requests.post(url, headers=headers, json=payload)

        print("Response status code:", response.status_code)
        print("Response reason:", response.reason)

        # Always print the response text before raising an error
        try:
            print("Raw response text:")
            print(response.text)
        except Exception as decode_error:
            print("Could not decode response text:", decode_error)

        response.raise_for_status()  # Raises 400/500 errors

        # Try to parse JSON response safely
        try:
            data = response.json()
            print("Parsed response JSON:")
            print(json.dumps(data, indent=4))
            return data
        except ValueError:
            print("Response was not valid JSON.")
            return None

    except requests.exceptions.HTTPError as e:
        print("HTTP Error:", e)
        print("Response content:", response.text if response else "No response body")
        return None
    except requests.exceptions.RequestException as e:
        print("Request Exception:", e)
        return None
    except Exception as e:
        print("Unexpected error:", e)
        return None


def get_shiiping_rate(payload):
    url = "https://api.shipbubble.com/v1/shipping/fetch_rates"
    API_KEY = os.getenv('API_KEY')
    print(API_KEY)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    try:
        print("Shipping rate payload:")
        print(json.dumps(payload, indent=4))

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        print("response Status:", response.status_code)
        print(json.dumps(data, indent=4))
        return data
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        if hasattr(e, 'response') and e.response is not None:
            print("Error response:", e.response.text)
        return None
    except Exception as e:
        print("Unexpected error in get_shiiping_rate:", e)
        return None


class GetShippingRate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from datetime import datetime
        try:
            user = request.user
            delivery_details = request.data.get('delivery_details')
            order_items = request.data.get('items')

            # Validate receiver address
            try:
                address = delivery_details.get('delivery_address')
                fullname = delivery_details.get('fullname')
                phone_number = delivery_details.get('phone_number')
                email_address = delivery_details.get('email_address')

                payload = {
                    "name": fullname,
                    "email": email_address,
                    "phone": phone_number,
                    "address": address,
                }

                try:
                    validated_address = ValidateAddress.objects.get(
                        address=address)
                    delivery_address_code = validated_address.address_code
                except ValidateAddress.DoesNotExist:
                    result = validate_address(payload)
                    if result and result.get('status') == 'success':
                        data = result.get('data')
                        ValidateAddress.objects.create(
                            name=data['name'],
                            email=data['email'],
                            phone=data['phone'],
                            address=data['address'],
                            postal_code=data['postal_code'],
                            address_code=data['address_code'],
                            latitude=data['latitude'],
                            longitude=data['longitude']
                        )
                        delivery_address_code = data['address_code']
                    else:
                        return Response({"error": "Error retrieving delivery address code"}, status=400)
            except Exception as e:
                logger.error(f"Address validation error: {str(e)}")
                return Response({"error": "Invalid delivery address"}, status=400)

            # Group items by store
            grouped_items = defaultdict(list)
            for item in order_items:
                store_id = item["store"]
                grouped_items[store_id].append(item)

            cleaned_data_list = []

            # Process each store group
            for store_id, items in grouped_items.items():
                try:
                    store = Store.objects.get(id=store_id)
                except Store.DoesNotExist:
                    return Response({"error": "Store does not exist"}, status=400)

                # Validate or create store address
                try:
                    validated_address = ValidateAddress.objects.get(
                        address=store.address1, owner=store.owner, email=store.owner.email
                    )
                    address_code = validated_address.address_code
                except ValidateAddress.DoesNotExist:
                    payload = {
                        'name': store.name,
                        'email': store.owner.email,
                        'address': store.address1,
                        'phone': str(store.owner.phone_number),
                    }
                    result = validate_address(payload)
                    if result and result.get('status') == 'success':
                        data = result.get('data')
                        validated_address = ValidateAddress.objects.create(
                            name=data['name'],
                            email=data['email'],
                            phone=data['phone'],
                            address=data['address'],
                            postal_code=data['postal_code'],
                            address_code=data['address_code'],
                            owner=store.owner,
                            latitude=data['latitude'],
                            longitude=data['longitude']
                        )
                        address_code = data['address_code']
                    else:
                        return Response({"error": f"Error retrieving address code for store {store.name}"}, status=400)

                # Check for free delivery items
                free_delivery_products = []
                products = []
                free_delivery = False

                for item in items:
                    try:
                        product_obj = Product.objects.get(id=item["product"])
                        products.append({
                            "product_id": product_obj.id,
                            "product_name": product_obj.title
                        })
                        if getattr(product_obj, "free_delivery", False):
                            free_delivery = True
                            free_delivery_products.append({
                                "product_id": product_obj.id,
                                "product_name": product_obj.title
                            })
                    except Product.DoesNotExist:
                        logger.warning(
                            f"Product with ID {item['product']} not found")

                # Calculate package info
                pickup_date = (datetime.now() + timedelta(days=1)
                               ).strftime("%Y-%m-%d")
                result = calculate_order_package(items)

                shipping_payload = {
                    "sender_address_code": address_code,
                    "reciever_address_code": delivery_address_code,
                    "pickup_date": pickup_date,
                    "category_id": result.get("package_items")[0].get('category_id'),
                    "package_items": result.get("package_items"),
                    "service_type": "pickup",
                    "delivery_instructions": "Please handle the package with care. Thank you, Movbay.",
                    "package_dimension": result.get("package_dimension")
                }

                # Third-party shipping rates
                response_data = get_shiiping_rate(shipping_payload)

                # MOVBAY internal pricing
                try:
                    delivery_validated_address = ValidateAddress.objects.get(
                        address=address, email=email_address)
                    destination = (delivery_validated_address.latitude,
                                   delivery_validated_address.longitude)
                except ValidateAddress.DoesNotExist:
                    destination = None

                try:
                    store_validated_address = ValidateAddress.objects.get(
                        owner=store.owner)
                    origin = (store_validated_address.latitude,
                              store_validated_address.longitude)
                except ValidateAddress.DoesNotExist:
                    origin = None

                summary = None
                movbay_fare = 1000

                if origin and destination:
                    summary = get_eta_distance_and_fare(origin, destination)
                    if summary and summary.get('fare_amount'):
                        weight_cost = result.get(
                            "package_dimension", {}).get("weight", 0) * 50
                        movbay_fare = summary.get(
                            'fare_amount') + 300 + weight_cost

                # Override fare for free delivery
                if free_delivery:
                    movbay_fare = 0

                # MOVBAY courier
                couriers = [
                    {
                        "courier_id": "movbay_dispatch",
                        "service_code": "MOVBAY00" + str(randint(0, 100)),
                        "courier_image": "https://res.cloudinary.com/dpoidbzwa/image/upload/v1760614229/MovBay_app_icon_yd0laf.png",
                        "discount": 0,
                        "ratings": 4.9,
                        "pickup_eta": "1 hour",
                        "delivery_eta": "Same day" if summary and summary.get("distance_km", 0) < 50 else "Next day",
                        "total": movbay_fare,
                        "free_delivery": free_delivery,
                        "free_delivery_products": free_delivery_products,
                        "products": products
                    }
                ]

                # Add third-party couriers if API call succeeds
                if response_data and response_data.get('status') == 'success':
                    third_party_couriers = response_data.get(
                        "data", {}).get("couriers", [])
                    couriers.extend([
                        {
                            "courier_id": c.get("courier_id"),
                            "service_code": c.get("service_code"),
                            "courier_image": c.get("courier_image"),
                            "discount": c.get("discount"),
                            "ratings": c.get("ratings"),
                            "pickup_eta": c.get("pickup_eta"),
                            "pickup_eta_time": c.get("pickup_eta_time"),
                            "delivery_eta": c.get("delivery_eta"),
                            "delivery_eta_time": c.get("delivery_eta_time"),
                            "total": 0 if free_delivery else c.get("total"),
                            "free_delivery": free_delivery,
                            "free_delivery_products": free_delivery_products,
                            "products": products
                        }
                        for c in third_party_couriers
                    ])

                    cleaned_data = {
                        "store_id": store.id,
                        "store": store.name,
                        "store_image": store.store_image_url,
                        "status": response_data.get("status"),
                        "message": response_data.get("message"),
                        "data": {
                            "request_token": response_data.get("data", {}).get("request_token"),
                            "couriers": couriers,
                        },
                    }
                else:
                    # Return only MOVBAY if third-party failed
                    cleaned_data = {
                        "store_id": store.id,
                        "store": store.name,
                        "status": "success",
                        "message": "MOVBAY courier available (third-party rates unavailable)",
                        "data": {
                            "request_token": None,
                            "couriers": couriers,
                        },
                    }

                cleaned_data_list.append(cleaned_data)

            return Response(cleaned_data_list, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in GetShippingRate: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred while calculating shipping rates"}, status=400)


class GetShipMentRate(APIView):
    # authentication_classes = [SessionAuthentication, JWTAuthentication]
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
    # authentication_classes = [SessionAuthentication, JWTAuthentication]
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
