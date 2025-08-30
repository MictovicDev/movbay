from .base import *
import os
import dj_database_url

DEBUG = True
#ALLOWED_HOSTS = ['*']
DOMAIN_NAME = os.getenv('DOMAIN_NAME', None)
IP = os.getenv('IP', None)
DOMAIN = os.getenv('DOMAIN', None)
ALT_DOMAIN = os.getenv('ALT_DOMAIN', None)
CORS_ORIGIN = os.getenv("CORS_ORIGIN", None)
CSRF_COOKIE = os.getenv("CSRF_COOKIE_DOMAIN", None)

ALLOWED_HOSTS = [DOMAIN_NAME, IP, DOMAIN, ALT_DOMAIN, 'localhost']

SESSION_COOKIE_DOMAIN = CSRF_COOKIE
CSRF_COOKIE_DOMAIN = CSRF_COOKIE

CORS_ALLOWED_ORIGINS = [
    'https://' + DOMAIN
]


CELERY_BEAT_SCHEDULE = {
    'delete-expired-statuses': {
        'task': 'stores.tasks.delete_expired_statuses',
        'schedule': 3600,
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
CELERY_BROKER_URL = os.getenv("REDIS_URL", None)
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL")
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
        "LOCATION": os.getenv("REDIS_URL", None),
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