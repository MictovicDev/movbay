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

STATIC_ROOT = BASE_DIR / "staticfiles"


STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}



CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_RESULT_EXPIRES = 86400


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



