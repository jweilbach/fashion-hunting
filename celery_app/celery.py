"""
Celery configuration and application setup
"""
import os
import sys
from pathlib import Path
from celery import Celery
from celery.schedules import crontab

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Celery configuration
app = Celery(
    'abmc_tasks',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    include=[
        'celery_app.tasks.feed_tasks',
        'celery_app.tasks.processing_tasks',
        'celery_app.tasks.scheduled_tasks'
    ]
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Los_Angeles',
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    
    # Result backend settings
    result_expires=86400,  # 24 hours
    result_persistent=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'fetch-all-feeds-every-hour': {
            'task': 'celery_app.tasks.scheduled_tasks.fetch_all_enabled_feeds',
            'schedule': crontab(minute=0),  # Every hour
        },
        'cleanup-old-results-daily': {
            'task': 'celery_app.tasks.scheduled_tasks.cleanup_old_results',
            'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        },
    },
)

# Auto-discover tasks
app.autodiscover_tasks(['celery_app.tasks'])

if __name__ == '__main__':
    app.start()
