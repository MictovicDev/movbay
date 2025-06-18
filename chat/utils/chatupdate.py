# utils/chat_update.py
import json, asyncio, redis
from django.conf import settings

class ChatUpdateHandler:
    def __init__(self, debounce_delay=2):
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
        self.debounce_delay = debounce_delay

    def send_chat_update(self, chat_id, message_data):
        return self._send_chat_update(chat_id, message_data)

    async def _send_chat_update(self, chat_id, message_data):
        debounce_key = f"chat_update_debounce:{chat_id}"
        update_key = f"chat_update_data:{chat_id}"

        self.redis_client.setex(update_key, self.debounce_delay + 1, json.dumps(message_data))

        if not self.redis_client.exists(debounce_key):
            self.redis_client.setex(debounce_key, self.debounce_delay, "1")
            asyncio.create_task(self._delayed_chat_update(chat_id))

    async def _delayed_chat_update(self, chat_id):
        await asyncio.sleep(self.debounce_delay)
        data = self.redis_client.get(f"chat_update_data:{chat_id}")
        if data:
            print(f"Sending update: {data}")
