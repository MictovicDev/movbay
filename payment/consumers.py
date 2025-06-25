# consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
import json

class PaymentConsumer(AsyncJsonWebsocketConsumer):
        
    async def connect(self):
        self.group_name = "payment_notifications"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def status_created(self, event):
        await self.send(text_data=json.dumps({
            "type": "status.created",
            "data": event["status"]
        }))
        
    async def payment_notifications(self, event):
        data = event.get("data")
        # Do something with payment data, e.g., send to frontend
        await self.send_json({
            "type": "payment_notifications",
            "data": data,
        })

        
    