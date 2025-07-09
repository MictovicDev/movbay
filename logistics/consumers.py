import os
import json
import redis
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from urllib.parse import parse_qs
from jwt import decode as jwt_decode
from django.conf import settings


redis_conn = redis.Redis(host='localhost', port=6379, db=0)

class DriverConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for driver-related real-time communication.
    Handles connection, disconnection, and incoming messages from drivers.
    """

    async def connect(self):
        # Get query string (as bytes), decode and parse
        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        if token is None:
            await self.close()
            return

        try:
            payload = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            self.user_id = payload.get('user_id') or payload.get('sub')  # adjust if needed
            self.email = payload.get('email')
            self.group_name = f"driver_{self.user_id}"

            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            redis_conn.set(f"driver:{self.user_id}:online", "1", ex=60*5)
            await self.accept()
        except Exception as e:
            print("JWT error:", e)
            await self.close()

    async def disconnect(self, close_code):
        """
        Handles WebSocket disconnection for a driver.
        - Removes the channel from its group.
        - Removes the online flag from Redis.
        """
        print(f"DriverConsumer: Driver {self.user_id} disconnected with code: {close_code}")

        # Discard this channel from the group it was added to
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        # Remove the online flag from Redis as the driver is no longer connected
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

                print(f"DriverConsumer: Received message from {self.user_id} - Type: {message_type}")

                if message_type == "heartbeat":
                    # Handle heartbeat message to keep the driver marked as online
                    redis_conn.set(f"driver:{self.user_id}:online", "1", ex=60*5)
                    print(f"DriverConsumer: Ping received from {self.user_id}, online status refreshed.")
                    # Optionally send a pong response back to the client
                    await self.send(text_data=json.dumps({"type": "heartbeat"}))
                elif message_type == "location_update":
                    # Handle driver location updates
                    location = data.get('location')
                    await self.handle_location_update(location)
                    
                elif message_type == "driver_online":
                    # Handle driver location updates
                    pass
                else:
                    # Handle any other generic message type
                    print(f"DriverConsumer: Unrecognized message type '{message_type}' from {self.user_id}.")
                    await self.send(text_data=json.dumps({
                        "type": "error",
                        "message": "Unrecognized message type."
                    }))

            except json.JSONDecodeError:
                print(f"DriverConsumer: Invalid JSON received from {self.user_id}: {text_data}")
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format."
                }))
            except Exception as e:
                print(f"DriverConsumer: Error processing message from {self.user_id}: {e}")
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": f"Server error: {str(e)}"
                }))
        else:
            print(f"DriverConsumer: Received empty message from {self.user_id}.")

    async def status_created(self, event):
        """
        Handler for 'status.created' messages sent to this driver's group.
        This is typically used to push new ride requests or status updates from the server
        to the connected driver client.
        """
        status_data = event.get("status")
        print(f"DriverConsumer: Sending status update to {self.user_id}: {status_data}")
        await self.send(text_data=json.dumps({
            "type": "status.created",
            "data": status_data
        }))

    async def handle_location_update(self, location_data):
        print(location_data)
        """
        Handles incoming 'location_update' messages from the driver.
        This is where you would process the driver's current latitude, longitude,
        and potentially update a database or Redis for real-time tracking.
        """
        if location_data and isinstance(location_data, dict):
            latitude = location_data.get('latitude')
            longitude = location_data.get('longitude')
            timestamp = location_data.get('timestamp') # Optional

            if latitude is not None and longitude is not None:
                print(f"Driver {self.user_id} location updated: Lat={latitude}, Lng={longitude}")
                # Example: Store location in Redis or update a database record
                # For a real application, you'd likely store this in a database
                # or a specialized geospatial database.
                redis_conn.geoadd("driver_locations", (longitude, latitude, self.user_id))
                redis_conn.set(f"driver:{self.user_id}:last_known_location", json.dumps(location_data))

                # Optionally, send a confirmation back to the driver
                await self.send(text_data=json.dumps({
                    "type": "location_update_ack",
                    "message": "Location received successfully."
                }))
            else:
                print(f"DriverConsumer: Invalid location data from {self.user_id}: {location_data}")
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Invalid location data format."
                }))
        else:
            print(f"DriverConsumer: Missing location data from {self.user_id}.")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Location data is missing or malformed."
            }))

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