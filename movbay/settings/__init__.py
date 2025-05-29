import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


load_dotenv(BASE_DIR / ".env")
# Get the environment setting
env = os.getenv("DJANGO_ENV","development")  # default to development


# Load the appropriate settings
if env == "production":
    from .production import *
else:
    from .development import *
