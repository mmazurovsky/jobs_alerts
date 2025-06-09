#!/bin/bash
set -e

# Deploy scraper service
cd linkedin_scraper_service
./deploy.sh
cd ..

# Deploy main project
cd main_project
./deploy.sh
cd ..

echo "All deployments completed successfully." 