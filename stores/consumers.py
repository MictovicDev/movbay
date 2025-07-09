import os
import json
import redis
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from urllib.parse import parse_qs
from jwt import decode as jwt_decode
from django.conf import settings


redis_conn = redis.Redis(host='localhost', port=6379, db=0)

class TrackingConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for driver-related real-time communication.
    Handles connection, disconnection, and incoming messages from drivers.
    """

    async def connect(self):
        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        print(token)
        if token is None:
            await self.close()
            return

        try:
            payload = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            self.user_id = payload.get('user_id') or payload.get('sub')  # adjust if needed
            self.email = payload.get('email')
            self.tracking_code = self.scope['url_route']['kwargs']['tracking_code']
            self.group_name = f"order_{self.tracking_code}"
            print(self.group_name)
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            await self.accept()
        except Exception as e:
            print("JWT error:", e)
            await self.close()

    async def disconnect(self, close_code):
        # Discard this channel from the group it was added to
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        redis_conn.delete(f"driver:{self.user_id}:online")
        print(f"DriverConsumer: Driver {self.user_id} marked offline.")


    async def receive(self, text_data=None, bytes_data=None):
        """
        Handles incoming messages from the WebSocket client (driver).
        Parses the message and dispatches it to appropriate handler methods
        based on the 'type' field in the JSON payload.
        """
        if text_data:
            try:
                data = json.loads(text_data)
                print(data)
                message_type = data.get("type")

                print(f"TrackConsumer: Received message from {self.user_id} - Type: {message_type}")

                if message_type == "heartbeat":
                    redis_conn.set(f"driver:{self.user_id}:online", "1", ex=60*5)
                    print(f"DriverConsumer: Ping received from {self.user_id}, online status refreshed.")
                    await self.send(text_data=json.dumps({"type": "heartbeat"}))
                    
                elif message_type == "track-order":
                    print(self.tracking_code)
                    await self.handle_order_tracking(self.tracking_code)
                    
                else:
                    # Handle any other generic message type
                    print(f"DriverConsumer: Unrecognized message type '{message_type}' from {self.user_id}.")
                    await self.send(text_data=json.dumps({
                        "type": "error",
                        "message": "Unrecognized message type."
                    }))

            except json.JSONDecodeError:
                print(f"TrackingConsumer: Invalid JSON received from {self.user_id}: {text_data}")
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format."
                }))
                
            except Exception as e:
                print(f"TrackingConsumer: Error processing message from {self.user_id}: {e}")
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": f"Server error: {str(e)}"
                }))
        else:
            print(f"TrackingConsumer: Received empty message from {self.user_id}.")

    async def order_status_update(self, event):
        # This method name must match the "type" in group_send
        await self.send_json({
            "type": "order_status_update",
            "order_id": event["order_id"],
            "status": event["status"]
        })
        
    async def handle_order_tracking(self, order_id):
        print(order_id)
        

    async def handle_ride_action(self, action_data):
        """
        Handles incoming 'ride_action' messages from the driver.
        This could be accepting, rejecting, or completing a ride.
        You would typically update the Ride model in your Django database here.
        """
        if action_data and isinstance(action_data, dict):
            ride_id = action_data.get('ride_id')
            action = action_data.get('action') # e.g., "accept", "reject", "complete"

            if ride_id and action:
                print(f"Driver {self.user_id} performed action '{action}' for Ride ID: {ride_id}")

                # Example: Update ride status in the database
                # You'll need to import your Ride model and use database_sync_to_async
                # from channels.db import database_sync_to_async
                # from rides.models import Ride # Assuming your Ride model is in rides/models.py

                # @database_sync_to_async
                # def update_ride_status(ride_id, new_status, driver_id):
                #     try:
                #         ride = Ride.objects.get(id=ride_id)
                #         if action == "accept":
                #             ride.status = "ACCEPTED"
                #             ride.driver_id = driver_id # Assign driver
                #             ride.start_time = timezone.now() # Set start time
                #         elif action == "reject":
                #             ride.status = "REJECTED" # Or some other status for rejected
                #             # Logic to find another driver
                #         elif action == "complete":
                #             ride.status = "COMPLETED"
                #             ride.end_time = timezone.now() # Set end time
                #             # Trigger fare calculation and payment processing
                #         ride.save()
                #         return True
                #     except Ride.DoesNotExist:
                #         return False

                # success = await update_ride_status(ride_id, action, self.user_id)
                # if success:
                #     await self.send(text_data=json.dumps({
                #         "type": "ride_action_ack",
                #         "message": f"Ride {ride_id} {action}ed successfully."
                #     }))
                # else:
                #     await self.send(text_data=json.dumps({
                #         "type": "error",
                #         "message": f"Ride {ride_id} not found or update failed."
                #     }))

                # For this example, just acknowledge the action
                await self.send(text_data=json.dumps({
                    "type": "ride_action_ack",
                    "message": f"Action '{action}' for ride {ride_id} received."
                }))
            else:
                print(f"DriverConsumer: Invalid ride action data from {self.user_id}: {action_data}")
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Invalid ride action data format."}))
                
    async def handle_driver_online(self, action_data):
        redis_conn.set(f"driver:{self.user_id}:online", "1", ex=60*5)
        pass