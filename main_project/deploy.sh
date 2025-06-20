#!/bin/bash
set -e

ENV=prod

export ENV
export DOCKER_BUILDKIT=1

echo "Building and pushing main_project from monorepo root..."

# Build with cache from the latest image
docker compose build --build-arg BUILDKIT_INLINE_CACHE=1 main_project

# Push the image to the registry
docker compose push main_project

echo "$ENV main_project build and push completed successfully."
