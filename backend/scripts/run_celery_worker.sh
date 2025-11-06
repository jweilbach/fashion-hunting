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
celery -A celery_app.celery worker --loglevel=info --concurrency=2
