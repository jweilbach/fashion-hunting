"""
Reports Router
Handles CRUD operations for media reports
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from uuid import UUID
import sys
from pathlib import Path
from math import ceil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api.database import get_db
from api import schemas
from api.auth import get_current_user, require_viewer, require_editor
from models.user import User
from repositories.report_repository import ReportRepository

router = APIRouter()


@router.get("/", response_model=schemas.ReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    provider: Optional[str] = Query(None, description="Filter by provider (RSS, TikTok, etc)"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment"),
    status: Optional[str] = Query(None, description="Filter by processing status"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    search: Optional[str] = Query(None, description="Search in title and summary"),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    List all reports for the current user's tenant with filtering and pagination

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 50, max: 100)
    - **provider**: Filter by provider
    - **sentiment**: Filter by sentiment
    - **status**: Filter by processing status
    - **start_date**: Filter from date
    - **end_date**: Filter to date
    - **search**: Search in title and summary
    """
    repo = ReportRepository(db)

    # Calculate offset
    skip = (page - 1) * page_size

    # Get reports with filters
    if search:
        reports = repo.search(current_user.tenant_id, search, limit=page_size)
        # Count total for search (approximate)
        total = len(reports)
    else:
        reports = repo.get_all(
            tenant_id=current_user.tenant_id,
            skip=skip,
            limit=page_size,
            provider=provider,
            status=status or 'completed',
            start_date=start_date,
            end_date=end_date
        )

        # Get total count efficiently using count method
        total = repo.count(
            tenant_id=current_user.tenant_id,
            provider=provider,
            status=status or 'completed',
            start_date=start_date,
            end_date=end_date
        )

    # Calculate pages
    pages = ceil(total / page_size)

    return schemas.ReportListResponse(
        items=[schemas.Report.model_validate(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{report_id}", response_model=schemas.Report)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get a specific report by ID"""
    repo = ReportRepository(db)
    report = repo.get_by_id(report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # Verify tenant access
    if report.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return schemas.Report.model_validate(report)


@router.get("/brand/{brand_name}", response_model=List[schemas.Report])
async def get_reports_by_brand(
    brand_name: str,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get all reports mentioning a specific brand"""
    repo = ReportRepository(db)
    reports = repo.get_by_brand(current_user.tenant_id, brand_name, limit=limit)

    return [schemas.Report.model_validate(r) for r in reports]


@router.patch("/{report_id}", response_model=schemas.Report)
@router.put("/{report_id}", response_model=schemas.Report)
async def update_report(
    report_id: UUID,
    report_update: schemas.ReportUpdate,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Update a report (sentiment, topic, brands, status)"""
    repo = ReportRepository(db)
    report = repo.get_by_id(report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # Verify tenant access
    if report.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update fields
    update_data = report_update.model_dump(exclude_unset=True)
    updated_report = repo.update(report_id, **update_data)

    return schemas.Report.model_validate(updated_report)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: UUID,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """Delete a report (requires editor or admin role)"""

    repo = ReportRepository(db)
    report = repo.get_by_id(report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # Verify tenant access
    if report.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    repo.delete(report_id)
    return None
