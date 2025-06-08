#!/bin/bash
# Helper script to run the main project locally with correct PYTHONPATH and environment variables
set -a
source main_project/.env
set +a
export PYTHONPATH="$(pwd)"
python main_project/app/main.py 