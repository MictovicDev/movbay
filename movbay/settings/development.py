from .base import *
import dj_database_url

# BASE_DIR = Path(__file__).resolve().parent.parent.parent



print(f"Base gave me this {BASE_DIR}")

DEBUG = True

ALLOWED_HOSTS = ['localhost']



SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None


# if os.getenv('DATABASE_URL'):
#     DATABASES = {
#     'default': dj_database_url.config(
#         default=os.environ.get('DATABASE_URL'),
#         conn_max_age=600,
#         ssl_require=True  # Required by Supabase
#     )
# }
# else:
#     # Keep your existing database configuration
#     pass


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}



CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")





CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",  # Just a unique identifier for the cache instance
    }
}


CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
           "hosts": [os.getenv("REDIS_URL")], 
        },
    },
}



STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]



