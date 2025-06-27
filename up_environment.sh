#!/bin/bash

# Environment startup script that handles environment switching for Docker Compose
# Usage: ./up_environment.sh [prod|test|dev] [service_name]

set -e

# Default environment is prod
ENVIRONMENT=${1:-prod}
SERVICE=${2:-all}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(prod|test|dev)$ ]]; then
    echo "❌ Error: Invalid environment '$ENVIRONMENT'"
    echo "Valid environments: prod, test, dev"
    exit 1
fi

echo "🚀 Bringing up environment: $ENVIRONMENT"

# Export environment variable for docker-compose
export ENV=$ENVIRONMENT

# Function to start a specific service
start_service() {
    local service_dir=$1
    local service_name=$2
    
    echo "📦 Starting $service_name with $ENVIRONMENT environment..."
    
    if [ ! -d "$service_dir" ]; then
        echo "⚠️  Warning: Directory $service_dir not found, skipping..."
        return
    fi
    
    cd "$service_dir"
    
    # Check if environment file exists
    if [ ! -f ".env.$ENVIRONMENT" ]; then
        echo "⚠️  Warning: .env.$ENVIRONMENT not found in $service_dir"
        echo "Please create .env.$ENVIRONMENT file with required variables"
    fi
    
    # Build and start the service
    docker-compose down
    docker-compose up -d --build
    
    echo "✅ $service_name started successfully"
    cd - > /dev/null
}

# Start services based on the service parameter
case $SERVICE in
    "all")
        echo "🔄 Starting all services..."
        start_service "core_service" "Core Service"
        start_service "linkedin_scraper_service" "LinkedIn Scraper Service"
        ;;
    "core")
        start_service "core_service" "Core Service"
        ;;
    "scraper")
        start_service "linkedin_scraper_service" "LinkedIn Scraper Service"
        ;;
    *)
        echo "❌ Error: Invalid service '$SERVICE'"
        echo "Valid services: all, core, scraper"
        exit 1
        ;;
esac

echo "🎉 Environment startup completed successfully!"
echo ""
echo "📋 Summary:"
echo "   Environment: $ENVIRONMENT"
echo "   Service(s): $SERVICE"
echo ""
echo "💡 Tips:"
echo "   - Check logs: docker-compose logs -f"
echo "   - View status: docker-compose ps"
echo "   - Stop services: docker-compose down" 