#!/bin/bash
set -e

MY_IMAGE=registry.digitalocean.com/mmazurovsky-registry/job_alerts_dev
MY_ENV=dev

export MY_IMAGE
export MY_ENV
export DOCKER_BUILDKIT=1

# Build with cache from the latest image
docker compose build --build-arg BUILDKIT_INLINE_CACHE=1 jobs_alerts

# Push the image to the registry
docker compose push jobs_alerts

echo "$MY_ENV Build and push completed successfully."
