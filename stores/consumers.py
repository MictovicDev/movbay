# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class StatusConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.store_id = self.scope['url_route']['kwargs']['store_id']
        self.group_name = f"store_{self.store_id}_statuses"

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
