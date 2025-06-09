#!/bin/bash
# Helper script to run the linkedin_scraper_service project locally with correct PYTHONPATH
set -a
source linkedin_scraper_service/.env
set +a
export PYTHONPATH="$(pwd)"
uvicorn linkedin_scraper_service.app.main:app --host 0.0.0.0 --port 8002 --reload 