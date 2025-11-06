#!/bin/bash
# Start Celery worker

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Start Celery worker with INFO logging
echo "Starting Celery worker..."
celery -A celery_app.celery worker --loglevel=info --concurrency=2
