from .base import *
import os
import dj_database_url

DEBUG = True
#ALLOWED_HOSTS = ['*']
ALLOWED_HOSTS = ['api.movbay.com', '162.0.231.122', 'www.movbay.com', 'movbay.com', 'localhost']

SESSION_COOKIE_DOMAIN = ".movbay.com"
CSRF_COOKIE_DOMAIN = ".movbay.com"

CORS_ALLOWED_ORIGINS = [
    "https://api.movbay.com",
]


CELERY_BEAT_SCHEDULE = {
    'delete-expired-statuses': {
        'task': 'stores.tasks.delete_expired_statuses',
        'schedule': 30,
    },
}


SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Logging configuration optimized for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


# settings.py debug
print("Loaded DB URL:", os.environ.get("DATABASE_URL"))

# Database configuration for production
if os.getenv('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
        )
    }
    # Override the engine to use PostGIS
else:
    # Keep your existing database configuration
    pass

print('Called Production')
# Redis configuratio
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_RESULT_EXPIRES = 86400

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
print("Loaded PRODUCTION settings") 


# settings.py

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [os.getenv("REDIS_URL")],
        },
    },
}

STATIC_ROOT = '/app/movbay/staticfiles'  # Match the volume path