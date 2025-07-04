#!/bin/bash
set -e

# Deploy scraper service
cd linkedin_scraper_service
./deploy.sh
cd ..

# Deploy main project
cd core_service
./deploy.sh
cd ..

echo "All deployments completed successfully." 