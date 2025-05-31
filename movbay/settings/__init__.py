# settings/__init__.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

env = os.getenv("DJANGO_ENV", "development").lower()
print("DJANGO_ENV =", env)

if env == "production":
    print("⚙️ Using PRODUCTION settings")
    from .production import *
elif env == "development":
    print("⚙️ Using DEVELOPMENT settings")
    from .development import *
else:
    raise Exception(f"Unknown DJANGO_ENV value: {env}")
