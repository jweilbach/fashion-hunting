"""
Job Execution Service - orchestrates scheduled job execution
"""
import logging
import time
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session

from models.job import ScheduledJob, JobExecution
from models.feed import FeedConfig
from models.brand import BrandConfig
from repositories.job_repository import JobRepository, JobExecutionRepository
from repositories.feed_repository import FeedRepository
from repositories.brand_repository import BrandRepository
from repositories.report_repository import ReportRepository
from ai_client import AIClient
from constants import ProviderType
from services.provider_factory import ProviderFactory as ContentProviderFactory
from services.processor_factory import ProcessorFactory

logger = logging.getLogger(__name__)


def get_source_type(provider: str) -> str:
    """
    Determine source_type from provider

    Args:
        provider: Provider name (e.g., 'RSS', 'INSTAGRAM', 'GOOGLE_SEARCH')

    Returns:
        Source type: 'digital', 'social', or 'broadcast'
    """
    provider_upper = provider.upper()

    # Digital: news articles, RSS feeds, web articles
    if provider_upper in ('RSS', 'GOOGLE_SEARCH', 'GOOGLE_NEWS', 'WEB', 'ARTICLE'):
        return 'digital'

    # Social: social media platforms
    if provider_upper in ('INSTAGRAM', 'TIKTOK', 'TWITTER', 'YOUTUBE', 'LINKEDIN', 'FACEBOOK'):
        return 'social'

    # Broadcast: TV, radio, podcasts
    if provider_upper in ('TV', 'BROADCAST', 'TVEYES', 'PODCAST', 'RADIO'):
        return 'broadcast'

    # Default to digital for unknown providers
    return 'digital'


class JobExecutionResult:
    """Result of job execution"""
    def __init__(
        self,
        status: str,
        execution_id: Optional[UUID] = None,
        items_processed: int = 0,
        items_failed: int = 0,
        message: str = ''
    ):
        self.status = status
        self.execution_id = execution_id
        self.items_processed = items_processed
        self.items_failed = items_failed
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'status': self.status,
            'execution_id': str(self.execution_id) if self.execution_id else None,
            'items_processed': self.items_processed,
            'items_failed': self.items_failed,
            'message': self.message
        }


class JobExecutionService:
    """
    Service for executing scheduled jobs

    Responsibilities:
    - Load job configuration from database
    - Fetch items from configured feeds
    - Process items using appropriate processors
    - Save results to reports table
    - Track execution status
    """

    def __init__(
        self,
        db: Session,
        ai_client: AIClient,
        job_repo: Optional[JobRepository] = None,
        execution_repo: Optional[JobExecutionRepository] = None,
        feed_repo: Optional[FeedRepository] = None,
        brand_repo: Optional[BrandRepository] = None,
        report_repo: Optional[ReportRepository] = None
    ):
        self.db = db
        self.ai_client = ai_client

        # Initialize repositories
        self.job_repo = job_repo or JobRepository(db)
        self.execution_repo = execution_repo or JobExecutionRepository(db)
        self.feed_repo = feed_repo or FeedRepository(db)
        self.brand_repo = brand_repo or BrandRepository(db)
        self.report_repo = report_repo or ReportRepository(db)

    def execute_job(self, job_id: UUID, task_id: Optional[str] = None) -> JobExecutionResult:
        """
        Execute a scheduled job

        Args:
            job_id: ID of the scheduled job to execute
            task_id: Optional Celery task ID for progress tracking

        Returns:
            JobExecutionResult with execution status and details
        """
        logger.info(f"Starting execution of scheduled job {job_id}")

        try:
            # Load job
            job = self._load_job(job_id)
            if not job:
                return JobExecutionResult(
                    status='error',
                    message=f'Job {job_id} not found'
                )

            # Create execution record
            execution = self._create_execution_record(job, task_id)

            try:
                # Extract configuration
                config = job.config or {}

                # Load feeds and brands
                feeds = self._load_feeds(job, config)
                brands = self._load_brands(job, config)

                # Fetch items from all feeds
                items = self._fetch_items_from_feeds(feeds, config)

                # Update total items count
                max_items = config.get('max_items_per_run', 10)
                total_items = min(len(items), max_items)
                execution.total_items = total_items
                self.db.commit()

                # Process items
                items_processed, items_failed = self._process_items(
                    items=items,
                    job=job,
                    config=config,
                    brands=brands,
                    execution=execution
                )

                # Mark execution as complete
                self._complete_execution(
                    execution=execution,
                    job=job,
                    items_processed=items_processed,
                    items_failed=items_failed
                )

                logger.info(f"Job execution completed: {items_processed} processed, {items_failed} failed")

                return JobExecutionResult(
                    status='success',
                    execution_id=execution.id,
                    items_processed=items_processed,
                    items_failed=items_failed,
                    message=f'Processed {items_processed} items successfully'
                )

            except Exception as e:
                # Mark execution as failed
                self._fail_execution(execution, str(e))
                raise

        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}", exc_info=True)
            return JobExecutionResult(
                status='error',
                message=str(e)
            )

    def _load_job(self, job_id: UUID) -> Optional[ScheduledJob]:
        """Load scheduled job from database"""
        job = self.job_repo.get_by_id(job_id)
        if job:
            logger.info(f"Executing job: {job.config.get('name', 'Unnamed')} for tenant {job.tenant_id}")
        return job

    def _create_execution_record(self, job: ScheduledJob, task_id: Optional[str] = None) -> JobExecution:
        """Create job execution tracking record"""
        execution = self.execution_repo.create(
            job_id=job.id,
            tenant_id=job.tenant_id,
            started_at=datetime.now(timezone.utc),
            status='running',
            items_processed=0,
            items_failed=0,
            celery_task_id=task_id
        )
        logger.info(f"Created execution record {execution.id} with task_id {task_id}")
        return execution

    def _load_feeds(self, job: ScheduledJob, config: Dict) -> List[FeedConfig]:
        """Load enabled feeds from database"""
        feed_ids = config.get('feed_ids', [])

        if not feed_ids:
            raise ValueError('No feeds configured for this job')

        logger.info(f"Loading {len(feed_ids)} feeds")

        feeds = self.db.query(FeedConfig).filter(
            FeedConfig.id.in_([UUID(fid) for fid in feed_ids]),
            FeedConfig.tenant_id == job.tenant_id,
            FeedConfig.enabled == True
        ).all()

        if not feeds:
            raise ValueError('No enabled feeds found')

        logger.info(f"Found {len(feeds)} enabled feeds to process")
        return feeds

    def _load_brands(self, job: ScheduledJob, config: Dict) -> List[str]:
        """Load brand names from database"""
        brand_ids = config.get('brand_ids', [])

        if not brand_ids:
            logger.info("No brands configured for tracking")
            return []

        brand_records = self.db.query(BrandConfig).filter(
            BrandConfig.id.in_([UUID(bid) for bid in brand_ids]),
            BrandConfig.tenant_id == job.tenant_id
        ).all()

        brands = [b.brand_name for b in brand_records]
        logger.info(f"Tracking {len(brands)} brands: {brands}")
        return brands

    def _fetch_items_from_feeds(
        self,
        feeds: List[FeedConfig],
        config: Dict
    ) -> List[Dict]:
        """
        Fetch items from all configured feeds using ProviderFactory.

        This method groups feeds by provider type and uses the ProviderFactory
        to dynamically instantiate the appropriate provider for each type.
        """
        items = []

        # Group feeds by provider type
        feeds_by_provider = {}
        for feed in feeds:
            provider_type = feed.provider.upper()
            if provider_type not in feeds_by_provider:
                feeds_by_provider[provider_type] = []
            feeds_by_provider[provider_type].append(feed)

        logger.info(f"Processing {len(feeds)} feeds across {len(feeds_by_provider)} providers")

        # Fetch from each provider type
        for provider_type, provider_feeds in feeds_by_provider.items():
            try:
                logger.info(f"Fetching from {len(provider_feeds)} {provider_type} feeds")

                # Convert FeedConfig objects to dict format expected by ProviderFactory
                feed_configs = []
                for feed in provider_feeds:
                    feed_config = {
                        'type': feed.feed_type,
                        'value': feed.feed_value,
                        'count': feed.fetch_count,
                        'feed_type': feed.feed_type,
                        'feed_value': feed.feed_value,
                        'fetch_count': feed.fetch_count,
                    }
                    feed_configs.append(feed_config)

                # Create provider using factory
                provider_config = config.get(provider_type.lower(), {}) if config else {}
                provider = ContentProviderFactory.create_provider(
                    provider_type=provider_type,
                    feed_configs=feed_configs,
                    config=provider_config
                )

                # Fetch items from provider
                provider_items = provider.fetch_items()
                logger.info(f"Fetched {len(provider_items)} items from {provider_type}")

                items.extend(provider_items)

            except Exception as e:
                logger.error(f"Error fetching from {provider_type}: {e}", exc_info=True)
                # Continue with other providers even if one fails
                continue

        if not items:
            raise ValueError('No items fetched from any provider')

        logger.info(f"Total items fetched from all providers: {len(items)}")
        return items


    def _process_items(
        self,
        items: List[Dict],
        job: ScheduledJob,
        config: Dict,
        brands: List[str],
        execution: JobExecution
    ) -> Tuple[int, int]:
        """
        Process fetched items using appropriate processors

        Returns:
            Tuple of (items_processed, items_failed)
        """
        # Build processor configuration
        processor_config = {
            'enable_html_brand_extraction': config.get('enable_html_brand_extraction', False),
            'max_html_size_bytes': config.get('max_html_size_bytes', 500000) if 'max_html_size_bytes' in config else 500000,
            'ignore_brand_exact': config.get('ignore_brand_exact', []),
            'ignore_brand_patterns': config.get('ignore_brand_patterns', []),
        }

        # Limit items to process
        max_items = config.get('max_items_per_run', 10)
        items_to_process = items[:max_items]

        items_processed = 0
        items_failed = 0

        # Cache processors by provider type
        processor_cache = {}

        for idx, item in enumerate(items_to_process):
            try:
                item_title = item.get('title', 'Untitled')
                logger.info(f"Processing item {idx+1}/{len(items_to_process)}: {item_title}")

                # Update progress in database
                execution.current_item_index = idx + 1
                execution.current_item_title = item_title[:500] if item_title else None
                execution.items_processed = items_processed
                execution.items_failed = items_failed
                self.db.commit()

                # Get or create processor
                provider = item.get('provider')
                if not provider:
                    raise ValueError("Item missing 'provider' field")

                if provider not in processor_cache:
                    processor_cache[provider] = ProcessorFactory.create_processor(
                        provider=provider,
                        ai_client=self.ai_client,
                        brands=brands,
                        config=processor_config
                    )

                processor = processor_cache[provider]

                # Process item
                processed_data, dedupe_key = processor.process_item(item)

                # Save to database
                self._save_report(job.tenant_id, dedupe_key, processed_data)

                items_processed += 1
                logger.info(f"Successfully processed item {idx+1}")

                # Rate limiting
                time.sleep(4 + random.uniform(0, 0.5))

            except Exception as e:
                logger.error(f"Failed to process item {idx+1}: {e}", exc_info=True)
                items_failed += 1
                self.db.rollback()
                continue

        return items_processed, items_failed

    def _save_report(
        self,
        tenant_id: UUID,
        dedupe_key: str,
        processed_data: Dict
    ) -> None:
        """Save processed report to database"""
        try:
            # Determine source_type from provider
            provider = processed_data['provider']
            source_type = get_source_type(provider)

            self.report_repo.create(
                tenant_id=tenant_id,
                dedupe_key=dedupe_key,
                source=processed_data['source'],
                provider=provider,
                source_type=source_type,
                brands=processed_data['brands'],
                title=processed_data['title'],
                link=processed_data['link'],
                summary=processed_data['summary'],
                full_text=processed_data['full_text'],
                sentiment=processed_data['sentiment'],
                topic=processed_data['topic'],
                est_reach=processed_data['est_reach'],
                timestamp=datetime.now(timezone.utc),
                processing_status='completed'
            )
        except Exception as db_error:
            # Check if duplicate
            if 'duplicate key' in str(db_error).lower() or 'uniqueviolation' in str(type(db_error).__name__).lower():
                logger.info("Skipping duplicate item - already exists in database")
                self.db.rollback()
            else:
                raise

    def _complete_execution(
        self,
        execution: JobExecution,
        job: ScheduledJob,
        items_processed: int,
        items_failed: int
    ) -> None:
        """Mark execution as complete and update job stats"""
        status = 'success' if items_failed == 0 else 'partial'

        self.execution_repo.complete(
            execution_id=execution.id,
            status=status,
            items_processed=items_processed,
            items_failed=items_failed,
            execution_log=f"Processed {items_processed} items, {items_failed} failed"
        )

        # Update job last_run info
        self.job_repo.update_last_run(
            job_id=job.id,
            status=status
        )

    def _fail_execution(self, execution: JobExecution, error_message: str) -> None:
        """Mark execution as failed"""
        try:
            self.execution_repo.complete(
                execution_id=execution.id,
                status='failed',
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Failed to update execution record: {e}")
