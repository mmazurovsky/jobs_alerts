#!/bin/bash

# Quick production deployment script
echo "🚀 Deploying to PRODUCTION environment..."
export ENV=prod
./deploy_environment.sh prod $1 