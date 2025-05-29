import os
from celery import Celery

Django_env = os.getenv('DJANGO_ENV', 'development')

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movbay.settings.production.py')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f"movbay.settings.{Django_env}")
app = Celery('movbay')
app.conf.broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


