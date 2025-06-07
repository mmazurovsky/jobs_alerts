#!/bin/bash
set -e

MY_IMAGE=registry.digitalocean.com/mmazurovsky-registry/linkedin_scraper_service
MY_ENV=prod

export MY_IMAGE
export MY_ENV
export DOCKER_BUILDKIT=1

echo "Building and pushing linkedin_scraper_service from monorepo root..."

# Build with cache from the latest image
docker compose build --build-arg BUILDKIT_INLINE_CACHE=1 linkedin_scraper_service

# Push the image to the registry
docker compose push linkedin_scraper_service

echo "$MY_ENV linkedin_scraper_service build and push completed successfully."
