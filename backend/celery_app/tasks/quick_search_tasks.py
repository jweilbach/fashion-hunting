"""
Celery tasks for Quick Search feature
"""
import sys
import logging
from pathlib import Path
from celery import current_task
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from celery_app.celery import app
from api.database import get_db
from services.quick_search_service import QuickSearchService

logger = logging.getLogger(__name__)


@app.task(bind=True, name='quick_search.execute')
def execute_quick_search_task(
    self,
    tenant_id: str,
    provider_type: str,
    search_value: str,
    search_type: str = 'search',
    result_count: int = 10
) -> Dict[str, Any]:
    """
    Execute a quick search as a Celery task with progress updates.

    Progress is updated via Celery task state updates.

    Args:
        tenant_id: Tenant ID
        provider_type: Provider type (INSTAGRAM, TIKTOK, etc.)
        search_value: Search term/hashtag/URL
        search_type: Type of search
        result_count: Number of results to fetch

    Returns:
        Dict with search results
    """
    logger.info(
        f"Quick search task started: task_id={self.request.id}, "
        f"tenant={tenant_id}, provider={provider_type}"
    )

    db = next(get_db())

    try:
        def progress_callback(data: Dict):
            """Update Celery task state with progress"""
            self.update_state(
                state='PROGRESS',
                meta={
                    'stage': data.get('stage'),
                    'message': data.get('message'),
                    'progress': data.get('progress'),
                    'current_item': data.get('current_item', 0),
                    'total_items': data.get('total_items', 0),
                }
            )

        # Execute search with progress callback
        service = QuickSearchService(
            db=db,
            tenant_id=tenant_id,
            progress_callback=progress_callback
        )

        result = service.execute_search(
            provider_type=provider_type,
            search_value=search_value,
            search_type=search_type,
            result_count=result_count
        )

        logger.info(
            f"Quick search task completed: task_id={self.request.id}, "
            f"items_fetched={result.get('items_fetched')}, "
            f"reports_created={result.get('reports_created')}"
        )

        return result

    except Exception as e:
        logger.error(f"Quick search task failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e),
            'items_fetched': 0,
            'reports_created': 0
        }
    finally:
        db.close()
