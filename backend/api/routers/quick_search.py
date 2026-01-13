# api/routers/quick_search.py
"""
Quick Search API - endpoints for executing one-off searches
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
import logging
import sys
from pathlib import Path
import json
import asyncio
from queue import Queue
import threading

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.quick_search_service import QuickSearchService
from api.auth import get_current_user, require_viewer
from api.database import get_db
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class QuickSearchRequest(BaseModel):
    """Request model for quick search"""
    provider_type: str = Field(..., description="Provider type (INSTAGRAM, TIKTOK, YOUTUBE, GOOGLE_SEARCH, RSS)")
    search_value: str = Field(..., description="Search term, hashtag, or URL")
    search_type: str = Field(default="search", description="Type of search (hashtag, keyword, search, url)")
    result_count: int = Field(default=10, ge=1, le=50, description="Number of results (1-50)")


class QuickSearchResponse(BaseModel):
    """Response model for quick search"""
    status: str
    message: str
    items_fetched: int
    reports_created: int


@router.post("/execute-async", status_code=202)
async def execute_quick_search_async(
    request: QuickSearchRequest,
    current_user: User = Depends(require_viewer)
):
    """
    Execute a quick search asynchronously with progress tracking.

    Returns immediately with a task_id that can be used to poll for progress.

    Returns:
        202 Accepted with task_id
    """
    from celery_app.tasks.quick_search_tasks import execute_quick_search_task

    logger.info(
        f"Quick search async: tenant={current_user.tenant_id}, "
        f"provider={request.provider_type}, value={request.search_value}"
    )

    # Start Celery task
    task = execute_quick_search_task.delay(
        tenant_id=str(current_user.tenant_id),
        provider_type=request.provider_type,
        search_value=request.search_value,
        search_type=request.search_type,
        result_count=request.result_count
    )

    return {
        "task_id": task.id,
        "status": "processing",
        "message": "Quick search started"
    }


@router.get("/status/{task_id}")
async def get_quick_search_status(
    task_id: str,
    current_user: User = Depends(require_viewer)
):
    """
    Get the status and progress of a quick search task.

    Returns:
        Task status with progress information
    """
    from celery_app.celery import app
    from celery.result import AsyncResult

    task = AsyncResult(task_id, app=app)

    if task.state == 'PENDING':
        return {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "message": "Task is queued..."
        }
    elif task.state == 'PROGRESS':
        return {
            "task_id": task_id,
            "status": "running",
            **task.info  # Contains stage, message, progress, current_item, total_items
        }
    elif task.state == 'SUCCESS':
        result = task.result
        return {
            "task_id": task_id,
            "status": "completed",
            "progress": 100,
            "result": result
        }
    elif task.state == 'FAILURE':
        return {
            "task_id": task_id,
            "status": "failed",
            "message": str(task.info),
            "progress": 0
        }
    else:
        return {
            "task_id": task_id,
            "status": task.state.lower(),
            "progress": 0
        }


@router.get("/execute-stream")
async def execute_quick_search_stream(
    provider_type: str,
    search_value: str,
    search_type: str = 'search',
    result_count: int = 10,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Execute a quick search with real-time progress updates via Server-Sent Events.

    Returns a stream of progress updates in SSE format.
    """
    logger.info(
        f"Quick search stream: tenant={current_user.tenant_id}, "
        f"provider={provider_type}, value={search_value}"
    )

    async def event_generator():
        """Generate SSE events with progress updates"""
        progress_queue = Queue()

        def progress_callback(data):
            """Callback to receive progress updates"""
            progress_queue.put(data)

        # Execute search in background with progress callback
        def run_search():
            try:
                service = QuickSearchService(
                    db=db,
                    tenant_id=str(current_user.tenant_id),
                    progress_callback=progress_callback
                )
                result = service.execute_search(
                    provider_type=provider_type,
                    search_value=search_value,
                    search_type=search_type,
                    result_count=result_count
                )
                # Send final result
                progress_queue.put({'type': 'result', 'data': result})
                progress_queue.put(None)  # Signal completion
            except Exception as e:
                logger.error(f"Quick search stream failed: {e}", exc_info=True)
                progress_queue.put({
                    'type': 'error',
                    'data': {'status': 'error', 'message': str(e)}
                })
                progress_queue.put(None)

        # Start search in background thread
        thread = threading.Thread(target=run_search)
        thread.start()

        # Stream progress updates
        while True:
            # Check for progress updates
            if not progress_queue.empty():
                update = progress_queue.get()
                if update is None:
                    break

                # Send SSE event
                event_type = update.get('type', 'progress')
                data = update.get('data', update)
                yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

            await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

        # Wait for thread to complete
        thread.join()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/execute", response_model=QuickSearchResponse)
async def execute_quick_search(
    request: QuickSearchRequest,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Execute a quick one-off search and save results as reports.

    This endpoint allows users to perform ad-hoc searches without creating
    persistent feeds or tasks. Results are immediately processed and saved
    to the database as regular reports.

    Args:
        request: Quick search parameters
        current_user: Current authenticated user (from auth)
        db: Database session

    Returns:
        QuickSearchResponse with status and counts

    Example:
        POST /api/v1/quick-search/execute
        {
            "provider_type": "INSTAGRAM",
            "search_value": "skincare",
            "search_type": "hashtag",
            "result_count": 20
        }
    """
    logger.info(
        f"Quick search request: tenant={current_user.tenant_id}, "
        f"provider={request.provider_type}, value={request.search_value}"
    )

    try:
        # Create service and execute search
        service = QuickSearchService(db=db, tenant_id=str(current_user.tenant_id))
        result = service.execute_search(
            provider_type=request.provider_type,
            search_value=request.search_value,
            search_type=request.search_type,
            result_count=request.result_count
        )

        if result['status'] == 'error':
            raise HTTPException(status_code=500, detail=result['message'])

        return QuickSearchResponse(**result)

    except Exception as e:
        logger.error(f"Quick search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
