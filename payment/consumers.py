# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class PaymentConsumer(AsyncWebsocketConsumer):
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
