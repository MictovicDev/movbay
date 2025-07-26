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

def get_nearby_drivers(store_lat, store_lng, radius_km=5):
    """
    Returns a list of available drivers within `radius_km` from store.
    """
    candidates = RiderProfile.objects.filter(is_online=True)
    print(candidates)
    nearby = []

    for driver in candidates:
        distance = haversine(store_lat, store_lng,
                             driver.latitude, driver.longitude)

        if candidates:
            if distance <= radius_km:
                nearby.append({
                    "driver_id": driver.id,
                    "distance_km": round(distance, 2),
                    "lat": driver.latitude,
                    "lng": driver.longitude
                })
            return sorted(nearby, key=lambda x: x["distance_km"])
        return None


class GoOnlineView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GoOnline_OfflineSerializer

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

                if order.status == 'out_for_delivery':
                    return Response({"message": "Ride already accepted."}, status=status.HTTP_400_BAD_REQUEST)
                
                if order.locked:
                    return Response({"message": "Ride has been Locked, other Rider accepted."}, status=status.HTTP_400_BAD_REQUEST)

                order.status = 'out_for_delivery'
                order.locked = True
                order.save()

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

        
        
        

