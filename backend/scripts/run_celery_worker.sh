#!/bin/bash
# Start Celery worker

# Navigate to project root (two levels up from scripts/)
cd "$(dirname "$0")/../.."

# Activate virtual environment
source .venv/bin/activate

# Set PYTHONPATH to include the backend directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"

# Change to backend directory
cd backend

# Start Celery worker with INFO logging
echo "Starting Celery worker..."
LOG_FILE="$(pwd)/logs/celery_worker.log"
echo "Logs writing to: $LOG_FILE"

# Run Celery directly - it will log to file via FileHandler
# We don't tail the log here since that's better done separately if needed
celery -A celery_app.celery worker --loglevel=info --concurrency=2
