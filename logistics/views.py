from users.models import RiderProfile
from .utils.haversine import haversine
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from .serializers import GoOnline_OfflineSerializer
from rest_framework.response import Response
from .serializers import UpdateLatLongSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import transaction
from stores.models import Order  # Adjust import path accordingly
from stores.tasks import send_push_notification  # Ensure this task exists
from .models import Ride
from .serializers import RideSerializer
from wallet.models import Wallet
from payment.models import Payment
from geopy.distance import geodesic
from django.shortcuts import get_object_or_404
from .models import RiderProfile, DeliveryPreference, BankDetail, KYC, PackageDelivery
from .serializers import (
    DeliveryPreferenceSerializer,
    BankDetailSerializer,
    KYCSerializer,
    TotalFareSerializer,
    PackageDeliverySerializer,
    GetNearbyRidersSerializer,
    GetPriceEstimateSerializer,
    GetNearbyRidesResponseSerializer,
    PackagePaymentDeliverySerializer
)
import math
from payment.factories import PaymentProviderFactory, PaymentMethodFactory
from django.db import models
from .tasks import upload_rider_files, upload_delivery_images
import logging
from base64 import b64encode
from logistics.utils.get_riders import get_nearby_drivers
from logistics.utils.eta import get_eta_distance_and_fare
from stores.utils.get_store_cordinate import get_coordinates_from_address
from rest_framework.exceptions import ValidationError, NotFound
from decimal import Decimal
import os
from payment.utils.helper import generate_tx_ref
from logistics.utils.handle_payment_package import handle_payment
from geopy.distance import geodesic

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GoOnlineView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GoOnline_OfflineSerializer

    def get(self, request):
        try:
            rider = RiderProfile.objects.get(user=request.user)
            serializer = self.serializer_class(rider)
            return Response(serializer.data, status=200)
        except Exception as e:
            print(str(e))
            return Response(str(e), status=400)

    def post(self, request):
        try:
            rider = RiderProfile.objects.get(user=request.user)
            serializer = self.serializer_class(rider, data=request.data)
            serializer.is_valid(raise_exception=True)
            print(serializer.validated_data)
            online = serializer.validated_data['online']
            rider.online = online
            rider.save()
            return Response({"details": serializer.data}, status=200)
        except Exception as e:
            print(str(e))
            return Response({'error': str(e)}, status=400)


class UpdateLatLongView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            rider = RiderProfile.objects.get(user=request.user)
            serializer = UpdateLatLongSerializer(rider, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"message": "Location updated", "data": serializer.data}, status=200)
        except RiderProfile.DoesNotExist:
            return Response({"error": "Rider profile not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class AcceptRide(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        ride = None
        riderprofile = get_object_or_404(RiderProfile, user=request.user)

        if request.user.user_type != 'Rider':
            return Response({"message": "Only Riders can accept rides."},
                            status=status.HTTP_400_BAD_REQUEST)

        ride_type = request.query_params.get(
            "type", "order")  # default = order

        try:
            with transaction.atomic():
                if ride_type == "order":
                    order = get_object_or_404(
                        Order.objects.select_for_update(), order_id=pk)
                    if order.ride_accepted:
                        print("order alread accpeted Error")
                        return Response({"message": "Ride already accepted."}, status=400)
                    if order.locked:
                        print("order locked Error")
                        return Response({"message": "Ride locked. Another rider accepted."}, status=400)

                    ride = order.ride.first()
                    if ride:
                        ride.accepted = True
                        ride.locked = True
                        ride.rider = request.user
                        ride.save()
                    order.locked = True
                    order.ride_accepted = True
                    tracking = order.order_tracking.first()
                    tracking.driver = riderprofile
                    tracking.save()
                    order.save()
                    transaction.on_commit(lambda: notify(ride_type))

                elif ride_type == "package-delivery":
                    ride = get_object_or_404(
                        Ride.objects.select_for_update(), id=pk)
                    if ride.accepted or ride.locked:
                        print('ride accepted Error')
                        return Response({"message": "Ride already accepted or locked."}, status=400)
                    if ride:
                        ride.accepted = True
                        ride.locked = True
                        ride.rider = request.user
                        ride.save()
                    transaction.on_commit(lambda: notify(ride_type))
                else:
                    print("Invalid type Error")
                    return Response({"message": "Invalid type. Must be 'order' or 'ride'."},
                                    status=status.HTTP_400_BAD_REQUEST)

                def notify(ride_type):
                    if ride_type == 'order':
                        message = "Ride has been accepted. Track its progress."
                    elif ride_type == 'package-delivery':
                        message = "Ride has been accepted. Please proceed to payment."
                    if ride_type == "order":
                        if order.buyer and order.buyer.device.exists():
                            send_push_notification.delay(
                                token=order.buyer.device.first().token,
                                title="Ride Accepted",
                                notification_type="Ride Update",
                                data=message
                            )
                        if order.store and order.store.owner.device.exists():
                            send_push_notification.delay(
                                token=order.store.owner.device.first().token,
                                title="Ride Accepted",
                                notification_type="Ride Update",
                                data=message
                            )
                    elif ride_type == "package-delivery":
                        send_push_notification.delay(
                            token=ride.package_delivery.sender.user.device.first().token,
                            title="Ride Accepted",
                            notification_type="Ride Update",
                            data=message
                        )
            return Response({"message": "Ride accepted successfully."}, status=200)

        except Exception as e:
            logger.error(f"Error in AcceptRide: {e}")
            return Response({"message": "Something went wrong."}, status=500)


class RideView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            # Get driver's location
            rider_profile = RiderProfile.objects.get(user=request.user)
            driver_lat = rider_profile.latitude
            driver_lon = rider_profile.longitude

            if not driver_lat or not driver_lon:
                return Response({"error": "Driver location not set"}, status=400)

            driver_location = (driver_lat, driver_lon)

            radius_km = 10  # search radius
            lat_range = radius_km / 111  # ~111 km per degree latitude
            lon_range = radius_km / \
                (111 * abs(math.cos(math.radians(driver_lat))) or 1e-6)

            min_lat = driver_lat - lat_range
            max_lat = driver_lat + lat_range
            min_lon = driver_lon - lon_range
            max_lon = driver_lon + lon_range

            # Filter candidates in bounding box
            candidates = Ride.objects.filter(
                latitude__range=(min_lat, max_lat),
                longitude__range=(min_lon, max_lon),
                accepted=False
            )

            # Final filter with exact geodesic
            nearby_rides = []
            for ride in candidates:
                if ride.latitude and ride.longitude:
                    ride_location = (ride.latitude, ride.longitude)
                    distance_km = geodesic(driver_location, ride_location).km
                    if distance_km <= radius_km:
                        nearby_rides.append(ride)

            serializer = RideSerializer(nearby_rides, many=True)
            return Response(serializer.data, status=200)

        except RiderProfile.DoesNotExist:
            return Response({"error": "Rider profile not found"}, status=404)
        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=500)


class RideDetailView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        ride = get_object_or_404(Ride, id=pk)
        serializer = RideSerializer(ride)
        return Response(serializer.data, status=200)


class CreateTerminalPackage(APIView):
    pass


class BaseRiderProfileView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]

    def get_rider_profile(self, user):
        print(user)
        rider = RiderProfile.objects.get(user=user)
        print(rider)
        try:
            return RiderProfile.objects.get(user=user)
        except RiderProfile.DoesNotExist:
            return None


class DeliveryPreferenceAPIView(BaseRiderProfileView):
    def get(self, request):
        rider = self.get_rider_profile(request.user)
        if not rider:
            return Response(
                {"detail": "Rider profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            pref = DeliveryPreference.objects.get(rider=rider)
            serializer = DeliveryPreferenceSerializer(pref)
            return Response(serializer.data)
        except DeliveryPreference.DoesNotExist:
            return Response(
                {"detail": "Delivery preferences not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request):
        rider = self.get_rider_profile(request.user)
        if not rider:
            return Response(
                {"detail": "Rider profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            pref = DeliveryPreference.objects.get(rider=rider)
            serializer = DeliveryPreferenceSerializer(pref, data=request.data)
        except DeliveryPreference.DoesNotExist:
            serializer = DeliveryPreferenceSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(rider=rider)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BankDetailAPIView(BaseRiderProfileView):

    def get(self, request):
        rider = self.get_rider_profile(request.user)
        if not rider:
            return Response(
                {"detail": "Rider profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            pref = BankDetail.objects.get(rider=rider)
            serializer = BankDetailSerializer(pref)
            return Response(serializer.data)
        except BankDetail.DoesNotExist:
            return Response(
                {"detail": "Delivery preferences not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request):
        rider = self.get_rider_profile(request.user)
        if not rider:
            return Response(
                {"detail": "Rider profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            pref = BankDetail.objects.get(rider=rider)
            serializer = BankDetailSerializer(pref, data=request.data)
        except BankDetail.DoesNotExist:
            serializer = BankDetailSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(rider=rider)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompletedRides(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            rides = Ride.objects.filter(
                rider=request.user, completed=True).count()
            return Response({"message": rides}, status=200)
        except Ride.DoesNotExist:
            return Response({"message": "No Completed Rides"}, status=204)
        except Exception as e:
            return Response({"message": str(e)}, status=500)


class TotalEarningsView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            total_earnings = Ride.objects.filter(rider=request.user, completed=True).aggregate(
                total=models.Sum('fare_amount'))['total'] or 0
            print(total_earnings)
            serializer = TotalFareSerializer({'total_fare': total_earnings})
            return Response(serializer.data, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class VerifiedRiderView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            rider = RiderProfile.objects.get(user=request.user)
            return Response({"verified": rider.verified}, status=200)
        except RiderProfile.DoesNotExist:
            return Response({"message": "No Rider Matching Profile"}, status=404)
        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=500)


class KYCDetailAPIView(BaseRiderProfileView):
    def get(self, request):
        rider = self.get_rider_profile(request.user)
        print(rider)
        if not rider:
            return Response(
                {"detail": "Rider profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        try:
            kyc = KYC.objects.get(rider=rider)
            serializer = KYCSerializer(kyc)
            return Response(serializer.data)
        except KYC.DoesNotExist:
            return Response(
                {"detail": "KYC details not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request):
        rider = self.get_rider_profile(request.user)
        if not rider:
            return Response(
                {"detail": "Rider profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            kyc = KYC.objects.get(rider=rider)
            serializer = KYCSerializer(kyc, data=request.data, partial=True)
        except KYC.DoesNotExist:
            serializer = KYCSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Process file uploads
        file_data = {}
        for field in ['nin', 'proof_of_address', 'drivers_licence']:
            if field in request.FILES:
                try:
                    file_data[field] = request.FILES[field].read()
                except Exception as e:
                    logger.error(f"Error reading {field} file: {str(e)}")
                    return Response(
                        {"detail": f"Error processing {field} file"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # Save the instance (either create or update)
        kyc = serializer.save(rider=rider)

        # Trigger background task if there are files to upload
        if file_data:
            upload_rider_files.delay(kyc.id, file_data)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if serializer.instance._state.adding else status.HTTP_200_OK
        )


class UserRides(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        ride = get_object_or_404(Ride, rider=request.user, id=pk)
        serializer = RideSerializer(ride)
        print(ride)
        return Response(serializer.data, status=200)


class PickedView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        ride_type = request.query_params.get(
            "type", "order")  # default = order

        if ride_type == 'order':
            order = get_object_or_404(Order, order_id=pk)
            order.status = 'out_for_delivery'
            order.save()
            ride = Ride.objects.get(order=order)
        elif ride_type == 'package-delivery':
            ride = get_object_or_404(Ride, id=pk)

        if not ride:
            return Response({"message": "You don't have a Ride Linked to this Order"}, status=400)
        if ride.accepted == False and order.ride_accepted == False:
            return Response({"message": "Ride hasn't been accepted yet"}, status=400)

        ride.out_for_delivery = True
        ride.save()
        return Response({"message": "Order marked for Delivery"}, status=200)


class GetPriceEstimate(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = GetPriceEstimateSerializer(data=request.data)
            print(request.data)
            if serializer.is_valid():
                pickup_address = serializer.validated_data['pickup_address']
                delivery_address = serializer.validated_data['delivery_address']
            pickup_coords = get_coordinates_from_address(pickup_address)
            delivery_coords = get_coordinates_from_address(delivery_address)
            if not pickup_coords:
                raise ValueError("Could not get store coordinates")

            destination = (delivery_coords.get('latitude'),
                           delivery_coords.get('longitude'))
            origin = (pickup_coords.get('latitude'),
                      pickup_coords.get('longitude'))

            # Get route summary
            summary = get_eta_distance_and_fare(origin, destination)
            return Response(summary, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting coordinates or summary: {str(e)}")
            return Response({"error": "Invalid addresses provided"}, status=status.HTTP_400_BAD_REQUEST)


class GetNearbyRiders(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = GetNearbyRidersSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        pickup_address = serializer.validated_data['pickup_address']
        delivery_address = serializer.validated_data['delivery_address']

        pickup_coords = get_coordinates_from_address(pickup_address)
        delivery_coords = get_coordinates_from_address(delivery_address)

        if not pickup_coords or not delivery_coords:
            return Response(
                {"error": "Invalid pickup or delivery coordinates"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        origin = (pickup_coords["latitude"], pickup_coords["longitude"])
        destination = (delivery_coords["latitude"],
                       delivery_coords["longitude"])

        try:
            riders = get_nearby_drivers(
                pickup_coords["latitude"], pickup_coords["longitude"], radius_km=5
            )

            data = []
            for rider in riders:
                driver = rider.get("driver")
                profile = driver.rider_profile
                rides_count = driver.user_ride.count()
                kyc = profile.kyc_verification.first()

                data.append({
                    "riders_name": driver.fullname,
                    "riders_id": driver.rider_profile.id,
                    "riders_picture": str(profile.profile_picture.url) if profile.profile_picture else None,
                    "verified": profile.verified,
                    "plate_number": kyc.plate_number if kyc else None,
                    "vehicle_color": kyc.vehicle_color if kyc else None,
                    "vehicle_type": kyc.vehicle_type if kyc else None,
                    "latitude": rider.get("lat"),
                    "longitude": rider.get("lng"),
                    "ride_count": rides_count,
                    "eta": get_eta_distance_and_fare(destination, (rider.get("lat"), rider.get("lng"))),
                })

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching nearby drivers: {str(e)}")
            return Response(
                {"error": "Could not fetch nearby riders"},
                status=status.HTTP_400_BAD_REQUEST,
            )


def notify_driver(driver, summary):
    """Send push notifications to available drivers"""
    errors = []
    try:
        try:
            devices = driver.user.device.all()
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
                f"Failed to notify driver {driver} {str(e)}")
            logger.error(f"Notification error: {str(e)}")

        if errors:
            logger.warning(f"Some notifications failed: {errors}")
    except Exception as e:
        logger.error(f"Critical error in notify_drivers: {str(e)}")
        raise


class SelectRideView(APIView):
    """
    View for selecting rides for Package Delivery
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        serializer = PackageDeliverySerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        drop_address = validated_data.get("drop_address")
        pick_address = validated_data.get("pick_address")
        package_images = validated_data.pop("package_images_list", [])

        # --- Fetch rider ---
        rider = RiderProfile.objects.filter(id=pk).first()
        if not rider:
            return Response(
                {"error": "Rider not found"}, status=status.HTTP_404_NOT_FOUND
            )
        if not rider.latitude or not rider.longitude:
            raise ValidationError(
                {"rider": "Rider location is not available."})

        # --- Resolve coordinates ---
        try:
            destination_coords = get_coordinates_from_address(drop_address)
            pickup_coords = get_coordinates_from_address(pick_address)
        except Exception:
            raise ValidationError(
                {"coordinates": "Unable to resolve pickup or drop address."}
            )

        pickup_origin = (pickup_coords["latitude"], pickup_coords["longitude"])
        destination = (
            destination_coords["latitude"], destination_coords["longitude"])
        origin = (rider.latitude, rider.longitude)

        # --- Fare calculation ---
        summary = get_eta_distance_and_fare(destination, origin)

        # --- Save delivery and ride ---
        packagedelivery = serializer.save(sender=request.user.user_profile)
        Ride.objects.get_or_create(
            rider=rider.user,
            distance_km=summary.get("distance_km"),
            duration_minutes=summary.get("duration_minutes"),
            fare_amount=summary.get("fare_amount"),
            delivery_type="Package",
            latitude=pickup_origin[0],
            longitude=pickup_origin[1],
            package_delivery=packagedelivery,
        )

        # --- Async image uploads ---
        for image in package_images:
            if image:
                try:
                    upload_delivery_images.delay(
                        packagedelivery.id,
                        {
                            "file_content": b64encode(image.read()).decode("utf-8"),
                            "filename": image.name,
                        },
                    )
                except Exception as e:
                    logger.warning(
                        f"Image upload failed for delivery {packagedelivery.id}: {str(e)}"
                    )

        # --- Notify driver only after DB commit ---
        transaction.on_commit(lambda: notify_driver(rider, summary))

        return Response(
            {"success": True, "data": PackageDeliverySerializer(
                packagedelivery).data},
            status=status.HTTP_201_CREATED,
        )


class PaymentDeliveryAPIView(APIView):
    """
    Handles Payment For Delivery.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PackagePaymentDeliverySerializer

    def post(self, request, pk):
        serializer = self.serializer_class(
            data=request.data, context={"request": request})
        try:
            if serializer.is_valid(raise_exception=True):
                validated_data = serializer.validated_data
                package = PackageDelivery.objects.get(
                    id=pk, sender=request.user.user_profile)
                payment_method = validated_data.get("payment_method")
                amount = package.amount
                provider_name = validated_data.get("provider_name")
                user = request.user
                if payment_method == 'wallet':
                    result = handle_payment(
                        payment_method, provider_name, amount, user, package)
                    print(result)
                    if result.get('status') == 'Completed':
                        package.amount += amount
                        wallet =  package.sender.user.wallet
                        # wallet.balance -= amount
                        # wallet.total_withdrawal += amount
                        # wallet.save()
                        package.save()
                        return Response({"message": "Created Succesfully"},
                                        status=status.HTTP_201_CREATED,
                                        )
                    else:
                        return Response({"Error Package Not created"}, status=400)

                elif payment_method == 'card' or payment_method == 'bank_transfer':
                    transaction_data = {
                        "email": request.user.email,
                        "amount": int(Decimal(validated_data['amount'])) * 100,
                        "reference": generate_tx_ref(),
                        "currency": "NGN",
                        "metadata": {
                            "user_id": str(request.user),
                            "payment_type": 'package-delivery',
                            # "cart_items": validated_data,
                        }, }
                    provider_name = validated_data['provider_name']
                    payment_method = validated_data['payment_method']
                    provider = PaymentProviderFactory.create_provider(
                        provider_name=provider_name)
                    method = PaymentMethodFactory.create_method(
                        method_name=payment_method)
                    transaction_data = method.prepare_payment_data(
                        transaction_data)
                    response = provider.initialize_payment(transaction_data)
                    return Response(response, status=status.HTTP_200_OK)
                else:
                    return Response({"Message": "Invalid Payment Method"}, status=400)

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(
                f"Unexpected error creating delivery: {str(e)}", exc_info=True)
            return Response(
                {"detail": "An unexpected error occurred while creating delivery."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class UserDeliveryHistory(APIView):
    """
    Handles retrieving the delivery history of the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        completed = request.query_params.get('completed', None)
        if isinstance(completed, str):
            completed = completed.capitalize()
        print(completed)
        if completed == 'True':
            deliveries = PackageDelivery.objects.filter(sender=request.user.user_profile, completed=True).order_by('-created_at')
            serializer = PackageDeliverySerializer(deliveries, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        deliveries = PackageDelivery.objects.filter(sender=request.user.user_profile, completed=False).order_by('-created_at')
        serializer = PackageDeliverySerializer(deliveries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PackageDeliveryDetailAPIView(APIView):
    """
    Handles retrieving, updating, and deleting a single delivery.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk, user):
        return get_object_or_404(PackageDelivery, pk=pk, rider__user=user)

    def get(self, request, pk):
        delivery = self.get_object(pk, request.user)
        serializer = PackageDeliverySerializer(delivery)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CancelRideView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        ride = get_object_or_404(Ride, id=pk, rider=request.user)
        if ride.completed:
            return Response({"message": "Cannot cancel a completed ride."}, status=400)
        if ride.cancelled:
            return Response({"message": "Ride is already cancelled."}, status=400)

        ride.accepted = False
        ride.locked = False  # Unlock the ride for others
        ride.save()

        # If linked to an order, update order status
        if ride.order:
            order = ride.order
            order.ride_accepted = False
            order.assigned = False
            order.locked = False
            order.save()
        return Response({"message": "Ride cancelled successfully."}, status=200)







