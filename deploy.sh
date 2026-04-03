#!/bin/bash

# Deployment script for Ubuntu production server

set -e

echo "🚀 Starting deployment..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env.prod exists
if [ ! -f .env.prod ]; then
    echo -e "${RED}Error: .env.prod file not found!${NC}"
    echo "Please create .env.prod with your production settings"
    exit 1
fi

# Load environment variables
source .env.prod

# Stop existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose -f docker-compose.prod.yml down

# Pull latest changes (if using git)
if [ -d .git ]; then
    echo -e "${YELLOW}Pulling latest changes...${NC}"
    git pull origin main || git pull origin master
fi

# Build and start containers
echo -e "${YELLOW}Building Docker images...${NC}"
docker-compose -f docker-compose.prod.yml build --no-cache

echo -e "${YELLOW}Starting containers...${NC}"
docker-compose -f docker-compose.prod.yml up -d

# Wait for database to be ready
echo -e "${YELLOW}Waiting for database...${NC}"
sleep 10

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate --noinput

# Collect static files
echo -e "${YELLOW}Collecting static files...${NC}"
docker-compose -f docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput

# Seed phases if needed
echo -e "${YELLOW}Seeding initial data...${NC}"
docker-compose -f docker-compose.prod.yml exec -T web python manage.py seed_phases || true

# Show running containers
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}Running containers:${NC}"
docker-compose -f docker-compose.prod.yml ps

echo -e "${GREEN}Application is now running!${NC}"
echo -e "Access your application at: https://${ALLOWED_HOSTS%%,*}"
