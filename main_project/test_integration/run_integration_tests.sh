#!/bin/bash
set -e

# Source test environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
cd "$SCRIPT_DIR/../../"  # Change to project root directory

# Find .env.test in main_project directory using absolute path
ENV_FILE="$SCRIPT_DIR/../.env.test"
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ .env.test not found in main_project directory ($ENV_FILE)"
  exit 1
fi

# Source the env file
set -a
. "$ENV_FILE"
set +a

echo "🧪 Running integration tests..."
pytest main_project/test_integration/test_premium_integration.py -v --tb=short 