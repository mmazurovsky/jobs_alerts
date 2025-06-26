#!/bin/bash

set -e

ENV="test"

export ENV

# Create network first if it doesn't exist
echo "Creating Docker network..."
docker network create jobs_alerts_network || true

# Function to add network config to docker-compose files
add_network_config() {
    echo "Adding network configuration to docker-compose files..."
    
    # LinkedIn scraper service - create a new file with network config
    cp linkedin_scraper_service/docker-compose.yml linkedin_scraper_service/docker-compose.yml.bak
    cat > linkedin_scraper_service/docker-compose.yml << 'EOF'
services:
  linkedin_scraper_service:
    build:
      context: ..
      dockerfile: linkedin_scraper_service/Dockerfile
    image: ${MY_IMAGE}
    env_file:
      - .env
    volumes:
      - ./logs:/home/scraper/app/logs
      - ./screenshots:/home/scraper/app/screenshots
      - /var/run/docker.sock:/var/run/docker.sock
      - ../shared:/home/scraper/app/shared:ro
      - ../:/app
    restart: unless-stopped
    ports:
      - "8002:8002"
    platform: linux/amd64
    networks:
      - jobs_alerts_network

networks:
  jobs_alerts_network:
    external: true
EOF
    
    # Main project - create a new file with network config
    cp main_project/docker-compose.yml main_project/docker-compose.yml.bak
    cat > main_project/docker-compose.yml << 'EOF'
services:
  main_project:
    build:
      context: ..
      dockerfile: main_project/Dockerfile
    image: registry.digitalocean.com/mmazurovsky-registry/main_project
    volumes:
      - ./logs:/home/scraper/app/logs
      - ./screenshots:/home/scraper/app/screenshots
      - /var/run/docker.sock:/var/run/docker.sock
      - ../shared:/home/scraper/app/shared:ro
      - ./tmp:/tmp
      - ../:/app
    restart: unless-stopped
    env_file:
      - .env.${ENV}
    ports:
      - "8001:8001"
    platform: linux/amd64
    networks:
      - jobs_alerts_network

networks:
  jobs_alerts_network:
    external: true
EOF
}

# Function to restore original docker-compose files
restore_docker_compose_files() {
    echo "Restoring original docker-compose files..."
    if [ -f linkedin_scraper_service/docker-compose.yml.bak ]; then
        mv linkedin_scraper_service/docker-compose.yml.bak linkedin_scraper_service/docker-compose.yml
    fi
    if [ -f main_project/docker-compose.yml.bak ]; then
        mv main_project/docker-compose.yml.bak main_project/docker-compose.yml
    fi
}

# Set up cleanup on exit
cleanup() {
    echo "Cleaning up..."
    docker compose -f main_project/docker-compose.yml down || true
    docker compose -f linkedin_scraper_service/docker-compose.yml down || true
    restore_docker_compose_files
}

# Trap Ctrl+C and cleanup on exit
trap cleanup SIGINT SIGTERM EXIT

# Add network configuration
add_network_config

echo "==== Starting LinkedIn Scraper Service ===="
echo "Starting linkedin_scraper_service Docker Compose..."
docker compose -f linkedin_scraper_service/docker-compose.yml up -d --build

# Verify scraper service is responding
echo "Verifying scraper service health..."
for i in {1..10}; do
    if curl -s http://localhost:8002/health > /dev/null 2>&1; then
        echo "✅ Scraper service is healthy"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ Scraper service not responding after 10 attempts"
        cleanup
        exit 1
    fi
    echo "Waiting for scraper service... (attempt $i/10)"
    sleep 2
done

echo "==== Starting Main Project ===="
echo "Starting main_project Docker Compose..."
docker compose -f main_project/docker-compose.yml --env-file main_project/.env.test up -d --build

echo "==== Verifying Network Connectivity ===="
sleep 5

# Verify network connectivity
echo "Verifying containers are on the same network..."
docker network inspect jobs_alerts_network | grep -A 20 "Containers"

# Test connectivity from main project to scraper service using Python
echo "Testing connectivity from main project to scraper service..."
MAIN_CONTAINER=$(docker compose -f main_project/docker-compose.yml ps -q main_project)
if [ -n "$MAIN_CONTAINER" ]; then
    if docker exec $MAIN_CONTAINER python -c "
import os
print('Environment variables:')
print(f'SCRAPER_SERVICE_URL: {os.getenv(\"SCRAPER_SERVICE_URL\", \"NOT SET\")}')
try:
    import httpx
    import asyncio
    async def test():
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get('http://linkedin_scraper_service:8002/health')
            return response.text
    result = asyncio.run(test())
    print('✅ Network connectivity test passed!')
    print(f'Response: {result}')
except Exception as e:
    print(f'❌ Network connectivity test failed: {e}')
" 2>/dev/null; then
        echo "✅ Network connectivity verified!"
    else
        echo "⚠️ Network connectivity test failed, but services may still work"
    fi
else
    echo "❌ Failed to find main project container"
fi

echo ""
echo "==== Both stacks are running and connected ===="
echo "LinkedIn Scraper Service: http://localhost:8002"
echo "Main Project: http://localhost:8001"
echo ""
echo "Tailing logs for all containers. Press Ctrl+C to stop and shut down both stacks."

# Tail logs for both stacks (interleaved)
docker compose -f linkedin_scraper_service/docker-compose.yml logs -f &
LOGS_PID2=$!
docker compose -f main_project/docker-compose.yml logs -f &
LOGS_PID1=$!

wait $LOGS_PID1 $LOGS_PID2