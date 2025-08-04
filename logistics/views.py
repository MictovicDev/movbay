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
from geopy.distance import geodesic
from django.shortcuts import get_object_or_404
from .models import RiderProfile, DeliveryPreference, BankDetail, KYC
from .serializers import (
    DeliveryPreferenceSerializer,
    BankDetailSerializer,
    KYCSerializer
)
from .tasks import upload_rider_files
import logging

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
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(order_id=pk)
                riderprofile = RiderProfile.objects.get(user=request.user)
                ride = order.ride.all()[0]
                
                rides = Ride.objects.filter(rider=request.user, completed=False)
                if rides:
                    return Response({"message": "You still have an uncompleted Ride."}, status=status.HTTP_400_BAD_REQUEST)
                
                if request.user.user_type != 'Rider':
                    return Response({"message": "Only Riders can accept rides."}, status=status.HTTP_400_BAD_REQUEST)
                
                if order.ride_accepted == True:
                    return Response({"message": "Ride already accepted."}, status=status.HTTP_400_BAD_REQUEST)

                if order.locked:
                    return Response({"message": "Ride has been Locked, other Rider accepted."}, status=status.HTTP_400_BAD_REQUEST)

                order.locked = True
                order.ride_accepted = True
                order_tracking = order.order_tracking.all()[0]
                order_tracking.driver = riderprofile
                order_tracking.save()
                ride.accepted = True
                ride.locked = True
                ride.rider = request.user
                order.save()
                ride.save()

                message = 'The ride has been accepted. Track its progress.'

                def notify():
                    try:
                        # Notify the buyer
                        if order.buyer and order.buyer.device.exists():
                            send_push_notification.delay(
                                token=order.buyer.device.first().token,
                                title='Ride Accepted',
                                notification_type='Ride Update',
                                data=message
                            )

                        # Notify the seller
                        if order.store and order.store.owner.device.exists():
                            send_push_notification.delay(
                                token=order.store.owner.device.first().token,
                                title='Ride Accepted',
                                notification_type='Ride Update',
                                data=message
                            )
                    except Exception as e:
                        print(f"Notification error: {str(e)}")

                transaction.on_commit(notify)

            return Response({"message": "Ride has been accepted."}, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({"message": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            print(f"Error in AcceptRide: {e}")
            return Response({"message": "Something went wrong."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        for field in ['nin', 'proof_of_address', 'drivers_license']:
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