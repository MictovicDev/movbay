# FROM python:3.11-slim

# # Set environment variables
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1

# # Set work directory
# WORKDIR /app

# # Install system dependencies
# RUN apt-get update \
#     && apt-get install -y --no-install-recommends \
#         build-essential \
#         libpq-dev \
#         postgresql-client \
#     && rm -rf /var/lib/apt/lists/*

# # Copy entire project into the container
# COPY . /app/

# # Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Create static/media folders (if not already present in repo)
# RUN mkdir -p /app/movbay/staticfiles /app/movbay/media

# # Gunicorn config (optional — if you have gunicorn_config.py)
# # Already copied by `COPY . /app/`, so no need to copy again

# # Collect static files (optional for production builds)
# # RUN python manage.py collectstatic --noinput

# # Default command to run the application
# CMD ["gunicorn", "--config", "/app/gunicorn_config.py", "movbay.wsgi:application"]


# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy entire project into the container
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create static/media folders (if not already present in repo)
RUN mkdir -p /app/movbay/staticfiles /app/movbay/media

# Gunicorn config (optional — if you have gunicorn_config.py)
# Already copied by `COPY . /app/`, so no need to copy again

# Collect static files (optional for production builds)
# RUN python manage.py collectstatic --noinput

# Default command to run the application
CMD ["gunicorn", "movbay.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--workers", "4", "--threads", "2", "--bind", "0.0.0.0:8000"]
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
#CMD ["uvicorn", "movbay.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]