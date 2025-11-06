#!/bin/bash
# Start Celery beat scheduler

# Navigate to project root (two levels up from scripts/)
cd "$(dirname "$0")/../.."

# Activate virtual environment
source .venv/bin/activate

# Set PYTHONPATH to include the backend directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"

# Change to backend directory
cd backend

# Remove old beat schedule file if exists
rm -f celerybeat-schedule.db

# Start Celery beat with INFO logging
echo "Starting Celery beat scheduler..."
celery -A celery_app.celery beat --loglevel=info
