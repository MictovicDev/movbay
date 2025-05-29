#!/bin/bash

# Docker cleanup script
echo "🧹 Cleaning up Docker environment..."

# Stop all containers
echo "Stopping all containers..."
sudo docker-compose down --remove-orphans

# Remove all containers
echo "Removing all containers..."
sudo docker container prune -f

# Remove all images
echo "Removing all images..."
sudo docker image prune -a -f

# Remove all volumes (WARNING: This will delete your data!)
echo "⚠️  WARNING: This will delete all Docker volumes including database data!"
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing all volumes..."
    sudo docker volume prune -f
else
    echo "Skipping volume cleanup."
fi

# Remove all networks
echo "Removing unused networks..."
sudo docker network prune -f

# Remove build cache
echo "Removing build cache..."
sudo docker builder prune -a -f

# System cleanup
echo "Running system cleanup..."
sudo docker system prune -a -f

echo "✅ Docker cleanup completed!"
echo "💡 Run './deploy.sh' to redeploy your application."
