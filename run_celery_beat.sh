#!/bin/bash
# Start Celery beat scheduler

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Remove old beat schedule file if exists
rm -f celerybeat-schedule.db

# Start Celery beat with INFO logging
echo "Starting Celery beat scheduler..."
celery -A celery_app.celery beat --loglevel=info
