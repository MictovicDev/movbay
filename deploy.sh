#!/bin/bash

# Deployment script for MovBay Django application
# Run as: chmod +x deploy.sh && ./deploy.sh

set -e

echo "🚀 Starting MovBay deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Stop and remove existing containers
print_status "Stopping existing containers..."
sudo docker-compose down --remove-orphans

# Clean up old images (optional)
print_status "Cleaning up old Docker images..."
sudo docker system prune -f

# Build and start services
print_status "Building and starting services..."
sudo docker-compose up -d --build

# Wait for database to be ready
print_status "Waiting for database to be ready..."
sleep 10

# Run database migrations
print_status "Running database migrations..."
sudo docker-compose exec web python manage.py makemigrations
sudo docker-compose exec web python manage.py migrate

# Collect static files
print_status "Collecting static files..."
sudo docker-compose exec web python manage.py collectstatic

# Create superuser (optional)
print_warning "Do you want to create a superuser? (y/n)"
read -r create_superuser
if [[ $create_superuser == "y" || $create_superuser == "Y" ]]; then
    sudo docker-compose exec web python manage.py createsuperuser
fi

# Obtain SSL certificate
# Reload Nginx to use SSL
print_status "Reloading Nginx with SSL configuration..."
sudo docker-compose exec nginx nginx -s reload

print_status "✅ Deployment completed successfully!"
print_status "Your application should be accessible at: https://api.movbay.com"

echo ""
print_warning "Don't forget to:"
echo "1. Update your environment variables in docker-compose.yml"
echo "2. Change default passwords"
echo "3. Update the email address in the SSL certificate command"
echo "4. Set up regular backups for your database"

# Show running containers
print_status "Currently running containers:"
sudo docker-compose ps
