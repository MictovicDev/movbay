from pathlib import Path
import redis
import os
from dotenv import load_dotenv
from datetime import timedelta
import redis.asyncio as aioredis


BASE_DIR = Path(__file__).resolve().parent.parent.parent


load_dotenv(BASE_DIR / ".env")



# redis_client = redis.StrictRedis(
#     host=os.getenv("REDIS_HOST", "redis"),
#     port=int(os.getenv("REDIS_PORT", 6379)),
#     db=0,
#     decode_responses=True
# )

redis_client = aioredis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)
