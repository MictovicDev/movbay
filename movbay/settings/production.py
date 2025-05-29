from .base import *
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url


BASE_DIR = Path(__file__).resolve().parent.parent.parent


load_dotenv(BASE_DIR / ".env")

env = os.getenv("DJANGO_ENV","production")  # default to development

# DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'
DEBUG = True
#ALLOWED_HOSTS = ['*']
ALLOWED_HOSTS = ['api.movbay.com', '162.0.231.122', 'www.movbay.com', 'movbay.com']

SESSION_COOKIE_DOMAIN = ".movbay.com"
CSRF_COOKIE_DOMAIN = ".movbay.com"

CORS_ALLOWED_ORIGINS = [
    "https://api.movbay.com",
]


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

# Database configuration for production
if os.getenv('DATABASE_URL'):
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(os.getenv('DATABASE_URL'))
    }
else:
    # Keep your existing database configuration
    pass

# Redis configuratio
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://localhost:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
