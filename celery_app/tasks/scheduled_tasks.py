"""
Scheduled Celery tasks for periodic execution
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from celery_app.celery import app

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@app.task(name='celery_app.tasks.scheduled_tasks.fetch_all_enabled_feeds')
def fetch_all_enabled_feeds() -> Dict[str, Any]:
    """
    Fetch all enabled feeds and process them using FeedProcessor class

    Returns:
        Dict with execution results
    """
    logger.info("Starting scheduled feed fetch task")

    try:
        # Import FeedProcessor from fetch_and_report_db
        from fetch_and_report_db import FeedProcessor
        import yaml

        # Load settings to get tenant_id
        config_path = Path(__file__).parent.parent.parent / "config"
        settings_path = config_path / "settings_unified.yaml"

        with open(settings_path) as f:
            settings = yaml.safe_load(f) or {}

        tenant_id = settings.get("tenant_id", "00000000-0000-0000-0000-000000000001")

        # Create processor and run
        logger.info(f"Creating FeedProcessor for tenant {tenant_id}")
        processor = FeedProcessor(tenant_id=tenant_id, config_path=str(config_path))

        try:
            result = processor.process_feeds()
            logger.info(f"Feed fetch task completed: {result}")
            return result
        finally:
            processor.close()

    except Exception as e:
        logger.error(f"Error in fetch_all_enabled_feeds task: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }


@app.task(name='celery_app.tasks.scheduled_tasks.cleanup_old_results')
def cleanup_old_results() -> Dict[str, Any]:
    """
    Cleanup old Celery task results from Redis

    Returns:
        Dict with cleanup results
    """
    logger.info("Starting cleanup of old task results")

    try:
        # Get all task result keys older than 7 days
        from celery.result import AsyncResult
        from datetime import datetime, timedelta

        # This is a placeholder - Celery automatically cleans up based on result_expires
        # You can add custom cleanup logic here if needed

        logger.info("Cleanup task completed successfully")
        return {
            'status': 'success',
            'message': 'Old results cleaned up'
        }

    except Exception as e:
        logger.error(f"Error in cleanup_old_results task: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }


@app.task(name='celery_app.tasks.scheduled_tasks.test_task')
def test_task(message: str = "Hello from Celery!") -> Dict[str, Any]:
    """
    Simple test task for verifying Celery setup

    Args:
        message: Test message to return

    Returns:
        Dict with test message
    """
    logger.info(f"Test task executed with message: {message}")
    return {
        'status': 'success',
        'message': message,
        'executed_at': str(Path(__file__).parent)
    }
