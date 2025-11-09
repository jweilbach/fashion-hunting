"""
Celery configuration and application setup
"""
import os
import sys
from pathlib import Path
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready, worker_shutdown, after_setup_logger
import logging

# Add src and api to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Setup logging - do this BEFORE creating Celery app
from api.logging_config import setup_logging, get_logger
log_level = os.getenv("LOG_LEVEL", "INFO")
# Don't setup logging here - Celery will override it
# We'll configure it via Celery's after_setup_logger signal instead
logger = get_logger(__name__)

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
        # DISABLED: Legacy hourly feed fetch - replaced by UI-driven job execution
        # All feeds are now managed through the database via the frontend UI
        # Users trigger jobs manually via the "Run" button which calls execute_scheduled_job
        # 'fetch-all-feeds-every-hour': {
        #     'task': 'celery_app.tasks.scheduled_tasks.fetch_all_enabled_feeds',
        #     'schedule': crontab(minute=0),  # Every hour
        # },
        'cleanup-old-results-daily': {
            'task': 'celery_app.tasks.scheduled_tasks.cleanup_old_results',
            'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        },
    },
)

# Auto-discover tasks
app.autodiscover_tasks(['celery_app.tasks'])


# Configure Celery logging AFTER Celery sets up its loggers
@after_setup_logger.connect
def setup_celery_logger(**kwargs):
    """Configure Celery logger with our custom format"""
    from api.logging_config import LOG_FORMAT, DATE_FORMAT

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)

    # Create handlers with our custom format
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    log_file = Path(__file__).parent.parent / "logs" / "celery_worker.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


# Celery worker lifecycle signals
@worker_ready.connect
def worker_ready_handler(sender, **kwargs):
    """Log when worker is ready"""
    logger.info("✅ Celery worker is ready and waiting for tasks")
    logger.info(f"Worker concurrency: 2 processes")
    logger.info(f"Broker: {os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')}")


@worker_shutdown.connect
def worker_shutdown_handler(sender, **kwargs):
    """Log when worker shuts down"""
    logger.info("🛑 Celery worker is shutting down")


if __name__ == '__main__':
    app.start()
