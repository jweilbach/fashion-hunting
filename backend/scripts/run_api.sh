#!/bin/bash
# Startup script for FastAPI server

# Navigate to project root (two levels up from scripts/)
cd "$(dirname "$0")/../.."
source .venv/bin/activate

# Set PYTHONPATH to include the backend directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"

# Run uvicorn from backend directory
cd backend
LOG_FILE="$(pwd)/logs/api.log"
echo "API logs writing to: $LOG_FILE"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | tee -a "$LOG_FILE"
