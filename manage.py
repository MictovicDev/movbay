from pathlib import Path
from dotenv import load_dotenv
import os
import sys

BASE_DIR = Path(__file__).resolve().parent


load_dotenv(BASE_DIR / ".env")

print(f".env file path: {BASE_DIR / '.env'}")
print(f".env file exists: {(BASE_DIR / '.env').exists()}")

django_env = os.getenv('DJANGO_ENV')


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f"movbay.settings.{django_env}")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
