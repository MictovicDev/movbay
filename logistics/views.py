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
    PackageDeliveryCreateSerializer,
    GetNearbyRidersSerializer,
    GetPriceEstimateSerializer,
    GetNearbyRidesResponseSerializer
)
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

        ride_type = request.query_params.get("type", "order")  # default = order

        try:
            with transaction.atomic():
                if ride_type == "order":
                    order = get_object_or_404(Order.objects.select_for_update(), order_id=pk)
                    if order.ride_accepted:
                        return Response({"message": "Ride already accepted."}, status=400)
                    if order.locked:
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

                elif ride_type == "package-delivery":
                    ride = get_object_or_404(Ride.objects.select_for_update(), id=pk)
                    if ride.accepted or ride.locked:
                        return Response({"message": "Ride already accepted or locked."}, status=400)

                else:
                    return Response({"message": "Invalid type. Must be 'order' or 'ride'."},
                                    status=status.HTTP_400_BAD_REQUEST)
                    
                def notify():
                    message = "Ride has been accepted. Track its progress."
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
                                token=ride.package_sender.device.first().token,
                                title="Ride Accepted",
                                notification_type="Ride Update",
                                data=message
                            )

                transaction.on_commit(notify)

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
            driver_location = (rider_profile.latitude, rider_profile.longitude)

            # Filter rides (e.g., not yet assigned or status = 'pending')
            all_rides = Ride.objects.all()

            # Filter rides within a certain radius (e.g., 10km)
            nearby_rides = []
            for ride in all_rides:
                if ride.latitude and ride.longitude:
                    ride_location = (ride.latitude, ride.longitude)
                    distance_km = geodesic(driver_location, ride_location).km
                    if distance_km <= 10:
                        nearby_rides.append(ride)

            serializer = RideSerializer(nearby_rides, many=True)
            return Response(serializer.data, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=404)

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
        order = get_object_or_404(Order, order_id=pk)
        ride = Ride.objects.get(order=order)
        if not ride:
            return Response({"message": "You don't have a Ride Linked to this Order"}, status=400)
        if ride.accepted == False and order.ride_accepted == False:
            return Response({"message": "Ride hasn't been accepted yet"}, status=400)
        order.status = 'out_for_delivery'
        ride.out_for_delivery = True
        order.save()
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
                    "riders_name": driver.id,
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


class PackageDeliveryView(APIView):
    """
    Handles listing all deliveries and creating new ones.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    
    
    def post(self, request, pk):
        serializer = PackageDeliveryCreateSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            validated_data = serializer.validated_data
            payment_method = validated_data.get("payment_method")
            amount = validated_data.get("amount")
            user = request.user
            if payment_method == 'wallet':
                handle_payment(payment_method, amount, user, validated_data, serializer, pk)
                if handle_payment.get('status') == 'Success':
                    return Response({"message": "Created Succesfully"},
                    status=status.HTTP_201_CREATED,
                )
            elif payment_method == 'package_delivery':
                print(validated_data)
                provider_name = validated_data['provider_name']
                payment_method = validated_data['payment_method']
                provider = PaymentProviderFactory.create_provider(
                    provider_name=provider_name)
                print(provider)
                method = PaymentMethodFactory.create_method(
                    method_name=payment_method)
                print(method)
                transaction_data = method.prepare_payment_data(
                    transaction_data)
                response = provider.initialize_payment(transaction_data)
                print(response)
                return Response(response, status=status.HTTP_200_OK)
                
                
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
