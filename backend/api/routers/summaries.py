"""
Summaries Router
Handles CRUD operations for AI-generated PDF summary documents (Brand 360)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from uuid import UUID
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api.database import get_db
from api import schemas
from api.auth import get_current_user, require_viewer, require_editor, require_admin
from models.user import User
from models.summary import Summary

router = APIRouter()


@router.get("/", response_model=schemas.SummaryListResponse)
async def list_summaries(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status (pending, generating, completed, failed)"),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    List all summaries for the current user's tenant.

    - **page**: Page number (default 1)
    - **page_size**: Items per page (default 20, max 100)
    - **status_filter**: Filter by generation status
    """
    query = db.query(Summary).filter(Summary.tenant_id == current_user.tenant_id)

    if status_filter:
        query = query.filter(Summary.generation_status == status_filter)

    # Order by most recent first
    query = query.order_by(desc(Summary.created_at))

    # Get total count
    total = query.count()

    # Paginate
    summaries = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [schemas.Summary.model_validate(s) for s in summaries],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }


@router.get("/recent", response_model=List[schemas.Summary])
async def get_recent_summaries(
    limit: int = Query(3, ge=1, le=10, description="Number of recent summaries to return"),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Get the most recent summaries for the dashboard.

    - **limit**: Number of summaries to return (default 3, max 10)
    """
    summaries = db.query(Summary).filter(
        Summary.tenant_id == current_user.tenant_id
    ).order_by(desc(Summary.created_at)).limit(limit).all()

    return [schemas.Summary.model_validate(s) for s in summaries]


@router.get("/{summary_id}", response_model=schemas.Summary)
async def get_summary(
    summary_id: UUID,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get a specific summary by ID"""
    summary = db.query(Summary).filter(Summary.id == summary_id).first()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found"
        )

    # Verify tenant access
    if summary.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return schemas.Summary.model_validate(summary)


@router.get("/{summary_id}/download")
async def download_summary(
    summary_id: UUID,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Download the PDF file for a summary.

    Returns the PDF file directly for download.
    Phase 1: Serves from local filesystem.
    Phase 2: Will return pre-signed S3 URL.
    """
    summary = db.query(Summary).filter(Summary.id == summary_id).first()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found"
        )

    # Verify tenant access
    if summary.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if summary is complete
    if summary.generation_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Summary is not ready. Status: {summary.generation_status}"
        )

    # Check if file exists
    if not summary.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found"
        )

    file_path = Path(summary.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found on disk"
        )

    # Generate filename from title
    safe_title = "".join(c for c in summary.title if c.isalnum() or c in " -_").strip()
    filename = f"{safe_title}.pdf" if safe_title else f"summary_{summary_id}.pdf"

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/pdf"
    )


@router.delete("/{summary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_summary(
    summary_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a summary and its associated PDF file.
    Requires admin role.
    """
    summary = db.query(Summary).filter(Summary.id == summary_id).first()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found"
        )

    # Verify tenant access
    if summary.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Delete file if exists
    if summary.file_path:
        file_path = Path(summary.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                # Log but don't fail if file deletion fails
                pass

    # Delete database record
    db.delete(summary)
    db.commit()

    return None
