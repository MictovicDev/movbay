"""
WSGI config for movbay project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# BASE_DIR = Path(__file__).resolve().parent.parent.parent
# load_dotenv(BASE_DIR / ".env")

# print(f"WSGI {BASE_DIR}")
from django.core.wsgi import get_wsgi_application
django_env = os.getenv('DJANGO_ENV')

print(os.getenv('DJANGO_ENV'))
# print('Me' + django_env)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f"movbay.settings.{django_env}")

application = get_wsgi_application()
