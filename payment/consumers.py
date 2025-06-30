# consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
import json

class PaymentConsumer(AsyncJsonWebsocketConsumer):
        
    async def connect(self):
        self.user = self.scope["user"]
        print(self.user)
        if self.user.is_anonymous:
            # Reject anonymous users
            await self.close()
            return
        
        self.group_name = f"{self.user.id}_payment_notifications"

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
            "type": "payment.notifications",
            "data": data,
        })

        
    