#!/bin/bash
set -e

MY_ENV=prod

export MY_ENV
export DOCKER_BUILDKIT=1

echo "Building and pushing main_project from monorepo root..."

# Build with cache from the latest image
docker compose build --build-arg BUILDKIT_INLINE_CACHE=1 main_project

# Push the image to the registry
docker compose push main_project

echo "$MY_ENV main_project build and push completed successfully."
