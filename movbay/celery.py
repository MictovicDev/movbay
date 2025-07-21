import os
from celery import Celery
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


load_dotenv(BASE_DIR / ".env")


Django_env = os.getenv('DJANGO_ENV')

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movbay.settings.production.py')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f"movbay.settings.{Django_env}")
app = Celery('movbay')
app.conf.broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

