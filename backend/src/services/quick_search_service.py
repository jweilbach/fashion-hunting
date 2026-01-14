# services/quick_search_service.py
"""
Quick Search Service - executes one-off searches without creating persistent feeds

Allows users to run ad-hoc searches and immediately see results without
going through the full feed creation workflow. Results are saved to the
database as regular reports.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from constants import ProviderType
from services.provider_factory import ProviderFactory
from services.processor_factory import ProcessorFactory
from services.job_execution_service import get_source_type
from repositories.brand_repository import BrandRepository
from repositories.report_repository import ReportRepository
from ai_client import AIClient

logger = logging.getLogger(__name__)


class QuickSearchService:
    """
    Service for executing quick one-off searches.

    Reuses existing provider and processor infrastructure but doesn't
    create persistent feed/task records in the database.
    """

    def __init__(self, db: Session, tenant_id: str, progress_callback: Optional[callable] = None):
        """
        Initialize quick search service for a tenant .

        Args:
            db: Database session
            tenant_id: UUID of the tenant performing the search
            progress_callback: Optional callback function for progress updates
        """
        self.db = db
        self.tenant_id = tenant_id
        self.ai_client = AIClient()
        self.brand_repo = BrandRepository(db)
        self.report_repo = ReportRepository(db)
        self.progress_callback = progress_callback

    def execute_search(
        self,
        provider_type: str,
        search_value: str,
        search_type: str = 'search',
        result_count: int = 10
    ) -> Dict[str, Any]:
        """
        Execute a quick search and save results as reports.

        Args:
            provider_type: Type of provider (INSTAGRAM, TIKTOK, YOUTUBE, GOOGLE_SEARCH, RSS)
            search_value: Search term, URL, or hashtag
            search_type: Type of search (hashtag, keyword, search, url, etc.)
            result_count: Number of results to fetch (max 50)

        Returns:
            Dict with status, items fetched, and reports created

        Example:
            >>> service = QuickSearchService(tenant_id='...')
            >>> result = service.execute_search('INSTAGRAM', 'skincare', 'hashtag', 20)
            >>> print(result)
            {'status': 'success', 'items_fetched': 20, 'reports_created': 18}
        """
        logger.info(
            f"Quick search: provider={provider_type}, "
            f"value={search_value}, type={search_type}, count={result_count}"
        )

        # Validate result count
        result_count = min(max(result_count, 1), 50)

        try:
            # Step 1: Get tracked brands for this tenant
            self._update_progress('loading', 'Loading brands...', 0, 3)
            brands = self._get_tracked_brands()
            logger.info(f"Tracking {len(brands)} brands for tenant {self.tenant_id}")

            # Step 2: Create provider and fetch items
            self._update_progress('fetching', f'Fetching from {provider_type}...', 1, 3)
            items = self._fetch_items(provider_type, search_value, search_type, result_count)
            logger.info(f"Fetched {len(items)} items from {provider_type}")

            if not items:
                self._update_progress('completed', 'No items found', 3, 3)
                return {
                    'status': 'success',
                    'message': 'No items found',
                    'items_fetched': 0,
                    'reports_created': 0,
                    'reports': []
                }

            # Step 3: Process items and create reports
            self._update_progress('processing', f'Processing {len(items)} items...', 2, 3)
            reports_created = self._process_and_save_items(items, provider_type, brands, len(items))
            logger.info(f"Created {reports_created} reports")

            self._update_progress('completed', f'Created {reports_created} reports', 3, 3)
            return {
                'status': 'success',
                'items_fetched': len(items),
                'reports_created': reports_created,
                'message': f"Found {len(items)} items, created {reports_created} reports"
            }

        except Exception as e:
            logger.error(f"Quick search failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
                'items_fetched': 0,
                'reports_created': 0
            }

    def _get_tracked_brands(self) -> List[str]:
        """Get list of tracked brands for the tenant"""
        brand_configs = self.brand_repo.get_all(self.tenant_id)
        return [brand.brand_name for brand in brand_configs]

    def _fetch_items(
        self,
        provider_type: str,
        search_value: str,
        search_type: str,
        result_count: int
    ) -> List[Dict]:
        """
        Fetch items using the appropriate provider.

        Creates a temporary feed config and uses ProviderFactory.
        """
        # Build feed config based on provider type
        feed_config = {
            'type': search_type,
            'value': search_value,
            'count': result_count
        }

        # Special handling for Google Search
        if provider_type.upper() == ProviderType.GOOGLE_SEARCH:
            provider = ProviderFactory.create_provider(
                provider_type=provider_type,
                feed_configs=[feed_config],
                config={
                    'results_per_query': result_count,
                    'date_restrict': 'd7'  # Last 7 days
                }
            )
        elif provider_type.upper() == ProviderType.RSS:
            # For RSS, search_value should be a URL
            provider = ProviderFactory.create_provider(
                provider_type=provider_type,
                feed_configs=[{'url': search_value}]
            )
        else:
            # Instagram, TikTok, YouTube
            provider = ProviderFactory.create_provider(
                provider_type=provider_type,
                feed_configs=[feed_config]
            )

        # Fetch items
        items = provider.fetch_items()
        return items

    def _process_and_save_items(
        self,
        items: List[Dict],
        provider_type: str,
        brands: List[str],
        total_items: int
    ) -> int:
        """
        Process items with appropriate processor and save as reports.

        Returns number of reports created.
        """
        # Get appropriate processor
        processor = ProcessorFactory.create_processor(
            provider=provider_type,
            ai_client=self.ai_client,
            brands=brands,
            config={}
        )

        reports_created = 0

        for idx, item in enumerate(items, 1):
            try:
                # Update progress for each item
                self._update_progress(
                    'processing',
                    f'Processing item {idx} of {total_items}...',
                    2 + (idx / total_items * 0.9),  # Progress from 2.0 to 2.9
                    3,
                    current_item=idx,
                    total_items=total_items
                )

                # Process item to extract brands, sentiment, etc.
                # Returns (processed_data, dedupe_key)
                processed_data, dedupe_key = processor.process_item(item)

                # Save to database as regular report using repository
                self._save_report(processed_data, dedupe_key, provider_type)
                reports_created += 1

            except Exception as e:
                logger.warning(f"Failed to process item: {e}")
                continue

        return reports_created

    def _update_progress(
        self,
        stage: str,
        message: str,
        current_step: float,
        total_steps: int,
        current_item: int = 0,
        total_items: int = 0
    ):
        """Send progress update via callback if available"""
        if self.progress_callback:
            progress_data = {
                'stage': stage,
                'message': message,
                'progress': int((current_step / total_steps) * 100),
                'current_item': current_item,
                'total_items': total_items
            }
            self.progress_callback(progress_data)

    def _save_report(self, processed: Dict, dedupe_key: str, provider_type: str):
        """Save processed item as a report in the database using repository"""
        # Determine source_type using shared helper function
        source_type = get_source_type(provider_type)

        # Use repository to create report - matches pattern from job_execution_service.py
        self.report_repo.create(
            tenant_id=self.tenant_id,
            dedupe_key=dedupe_key,
            source=processed.get('source', ''),
            provider=processed.get('provider', provider_type),
            source_type=source_type,
            brands=processed.get('brands', []),
            title=processed.get('title', ''),
            link=processed.get('link', ''),
            summary=processed.get('summary', ''),
            full_text=processed.get('full_text', ''),
            sentiment=processed.get('sentiment', 'neutral'),
            topic=processed.get('topic', 'product'),
            est_reach=processed.get('est_reach', 0),
            timestamp=datetime.now(),
            processing_status='completed'
        )
