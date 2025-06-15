#!/bin/bash

set -e

ENVIRONMENT="test"

export ENVIRONMENT

# Start linkedin_scraper_service stack
echo "Starting linkedin_scraper_service Docker Compose..."
docker compose -f linkedin_scraper_service/docker-compose.yml up -d --build

# Create network if it doesn't exist
docker network create jobs_alerts_network || true

# Start main_project stack with .env.test
echo "Starting main_project Docker Compose..."
docker compose -f main_project/docker-compose.yml --env-file main_project/.env.test up -d --build

echo "Both stacks are running."
echo "Tailing logs for all containers. Press Ctrl+C to stop and shut down both stacks."

# Trap Ctrl+C and stop both stacks on exit
trap 'echo "\nStopping both stacks..."; docker compose -f main_project/docker-compose.yml down; docker compose -f linkedin_scraper_service/docker-compose.yml down; exit 0' SIGINT

# Tail logs for both stacks (interleaved)
docker compose -f linkedin_scraper_service/docker-compose.yml logs -f &
LOGS_PID2=$!
docker compose -f main_project/docker-compose.yml logs -f &
LOGS_PID1=$!


wait $LOGS_PID1 $LOGS_PID2