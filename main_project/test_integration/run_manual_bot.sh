#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
cd "$SCRIPT_DIR"
if [ ! -f .env.test ]; then
  echo ".env.test not found"; exit 1;
fi
set -a; source .env.test; set +a
python test_bot_manual.py 