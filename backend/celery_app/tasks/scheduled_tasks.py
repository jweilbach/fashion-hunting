"""
Scheduled Celery tasks for periodic execution
"""
import sys
import logging
import hashlib
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


@app.task(name='celery_app.tasks.scheduled_tasks.execute_scheduled_job')
def execute_scheduled_job(job_id: str) -> Dict[str, Any]:
    """
    Execute a specific scheduled job by loading its configuration from the database

    This task:
    1. Loads the ScheduledJob from the database
    2. Reads the feed_ids and brand_ids from the job's config
    3. Fetches feed URLs and brand names from the database
    4. Processes those specific feeds
    5. Creates a JobExecution record to track progress
    6. Saves results to the reports table

    Args:
        job_id: UUID of the scheduled job to execute

    Returns:
        Dict with execution results
    """
    from datetime import datetime, timezone
    from uuid import UUID

    logger.info(f"Starting execution of scheduled job {job_id}")

    # Import database models and repositories
    from models.base import SessionLocal
    from models.job import ScheduledJob, JobExecution
    from models.feed import FeedConfig
    from models.brand import BrandConfig
    from models.report import Report
    from repositories.report_repository import ReportRepository
    from repositories.brand_repository import BrandRepository

    # Import content processing components
    from ai_client import AIClient
    from providers.rss_provider import RSSProvider
    from fetch_and_report_db import fetch_full_article_text
    import os
    import time
    import random

    db = SessionLocal()
    execution_id = None

    try:
        # Load the scheduled job
        job = db.query(ScheduledJob).filter(ScheduledJob.id == UUID(job_id)).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return {'status': 'error', 'message': f'Job {job_id} not found'}

        logger.info(f"Executing job: {job.config.get('name', 'Unnamed')} for tenant {job.tenant_id}")

        # Create JobExecution record
        execution = JobExecution(
            job_id=job.id,
            tenant_id=job.tenant_id,
            started_at=datetime.now(timezone.utc),
            status='running',
            items_processed=0,
            items_failed=0
        )
        db.add(execution)
        db.commit()
        execution_id = execution.id
        logger.info(f"Created execution record {execution_id}")

        # Extract configuration
        config = job.config or {}
        feed_ids = config.get('feed_ids', [])
        brand_ids = config.get('brand_ids', [])

        logger.info(f"Job configured with {len(feed_ids)} feeds and {len(brand_ids)} brands")

        if not feed_ids:
            execution.status = 'failed'
            execution.error_message = 'No feeds configured for this job'
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {'status': 'error', 'message': 'No feeds configured'}

        # Load feeds from database
        feeds = db.query(FeedConfig).filter(
            FeedConfig.id.in_([UUID(fid) for fid in feed_ids]),
            FeedConfig.tenant_id == job.tenant_id,
            FeedConfig.enabled == True
        ).all()

        if not feeds:
            execution.status = 'failed'
            execution.error_message = 'No enabled feeds found'
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {'status': 'error', 'message': 'No enabled feeds found'}

        logger.info(f"Found {len(feeds)} enabled feeds to process")

        # Load brands from database
        brands = []
        if brand_ids:
            brand_records = db.query(BrandConfig).filter(
                BrandConfig.id.in_([UUID(bid) for bid in brand_ids]),
                BrandConfig.tenant_id == job.tenant_id
            ).all()
            brands = [b.brand_name for b in brand_records]
            logger.info(f"Tracking {len(brands)} brands: {brands}")

        # Initialize AI client and repositories
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not set")

        ai_client = AIClient(api_key=openai_key)
        report_repo = ReportRepository(db)

        # Prepare RSS feed URLs (filter for RSS provider only for now)
        rss_feed_urls = [f.feed_value for f in feeds if f.provider.upper() == 'RSS']

        if not rss_feed_urls:
            execution.status = 'failed'
            execution.error_message = 'No RSS feeds configured (only RSS supported currently)'
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {'status': 'error', 'message': 'No RSS feeds configured'}

        logger.info(f"Processing {len(rss_feed_urls)} RSS feeds")

        # Create RSS provider and fetch items
        rss_provider = RSSProvider(rss_feed_urls)
        items = rss_provider.fetch_items()
        logger.info(f"Fetched {len(items)} items from RSS feeds")

        # Process items (limit to avoid long execution)
        max_items = config.get('max_items_per_run', 10)
        items_processed = 0
        items_failed = 0

        for idx, item in enumerate(items[:max_items]):
            try:
                logger.info(f"Processing item {idx+1}/{min(len(items), max_items)}: {item.get('title')}")

                # Fetch full article text and HTML
                logger.info(f"Fetching full article from: {item.get('link')}")
                full_text, html_bytes = fetch_full_article_text(
                    item.get("link", ""),
                    item.get("title", ""),
                    item.get("raw_summary", ""),
                    extra_meta_names=[],
                    extra_meta_properties=[],
                    extra_itemprops=[],
                    return_html=True
                )

                # Fallback to title + summary if fetch failed
                if len(full_text) < 100:
                    logger.warning(f"Full article fetch failed, using RSS summary only")
                    full_text = f"{item.get('title', '')}\n\n{item.get('raw_summary', '')}"
                    html_bytes = None

                # Use AI to analyze the text content
                logger.info(f"Analyzing article text ({len(full_text)} chars)")
                analysis = ai_client.classify_summarize(full_text, brands)

                # Get brands from text analysis
                mentioned_brands = analysis.get('brands', [])
                logger.info(f"Text analysis extracted brands: {mentioned_brands}")

                # Also extract brands from HTML if available
                if html_bytes:
                    logger.info(f"Extracting brands from HTML ({len(html_bytes)} bytes)")
                    try:
                        brands_from_html = ai_client.ai_extract_brands_from_raw_html(
                            html_bytes,
                            ignore_exact=[],
                            ignore_patterns=[]
                        )
                        logger.info(f"HTML analysis extracted brands: {brands_from_html}")

                        # Merge brands from both sources (avoid duplicates)
                        seen = set(b.lower() for b in mentioned_brands)
                        for b in brands_from_html:
                            if b.lower() not in seen:
                                mentioned_brands.append(b)
                                seen.add(b.lower())

                        logger.info(f"Combined brands after HTML merge: {mentioned_brands}")
                    except Exception as html_error:
                        logger.warning(f"HTML brand extraction failed: {html_error}")

                # Generate dedupe_key from title + link
                dedupe_content = f"{item.get('title', '')}{item.get('link', '')}"
                dedupe_key = hashlib.sha256(dedupe_content.encode()).hexdigest()

                # Create report in database
                try:
                    report_repo.create(
                        tenant_id=job.tenant_id,
                        dedupe_key=dedupe_key,
                        source=item.get('source', 'RSS'),
                        provider='RSS',
                        brands=mentioned_brands,
                        title=item.get('title', ''),
                        link=item.get('link', ''),
                        summary=analysis.get('short_summary', ''),
                        full_text=full_text[:5000],  # Limit size
                        sentiment=analysis.get('sentiment', 'neutral'),
                        topic=analysis.get('topic', 'general'),
                        est_reach=analysis.get('est_reach', 0),
                        timestamp=datetime.now(timezone.utc),
                        processing_status='completed'
                    )

                    items_processed += 1
                    logger.info(f"Successfully processed item {idx+1}")

                except Exception as db_error:
                    # Check if it's a duplicate key error
                    if 'duplicate key' in str(db_error).lower() or 'uniqueviolation' in str(type(db_error).__name__).lower():
                        logger.info(f"Skipping item {idx+1} - already exists in database")
                        db.rollback()  # Rollback the failed transaction
                        # Don't count as failed - it's already in the database
                    else:
                        # Some other database error - re-raise it
                        raise

                # Rate limiting
                time.sleep(4 + random.uniform(0, 0.5))

            except Exception as e:
                logger.error(f"Failed to process item {idx+1}: {e}", exc_info=True)
                items_failed += 1
                db.rollback()  # Ensure session is clean for next iteration
                continue

        # Update execution record
        execution.status = 'success' if items_failed == 0 else 'partial'
        execution.items_processed = items_processed
        execution.items_failed = items_failed
        execution.completed_at = datetime.now(timezone.utc)
        execution.execution_log = f"Processed {items_processed} items, {items_failed} failed"

        # Update job last_run info
        job.last_run = datetime.now(timezone.utc)
        job.last_status = execution.status
        job.run_count = (job.run_count or 0) + 1

        db.commit()

        logger.info(f"Job execution completed: {items_processed} processed, {items_failed} failed")

        return {
            'status': 'success',
            'execution_id': str(execution_id),
            'items_processed': items_processed,
            'items_failed': items_failed,
            'message': f'Processed {items_processed} items successfully'
        }

    except Exception as e:
        logger.error(f"Error executing job {job_id}: {e}", exc_info=True)

        # Update execution record if it exists
        if execution_id:
            try:
                execution = db.query(JobExecution).filter(JobExecution.id == execution_id).first()
                if execution:
                    execution.status = 'failed'
                    execution.error_message = str(e)
                    execution.completed_at = datetime.now(timezone.utc)
                    db.commit()
            except Exception as update_error:
                logger.error(f"Failed to update execution record: {update_error}")

        return {
            'status': 'error',
            'message': str(e)
        }

    finally:
        db.close()
