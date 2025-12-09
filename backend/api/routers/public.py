"""
Public Router - Authenticated endpoints for dashboard
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api.database import get_db
from api.auth import require_viewer
from models.user import User
from models.report import Report
from models.brand import BrandConfig
from models.feed import FeedConfig

router = APIRouter()


@router.get("/overview")
async def get_overview(
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Get dashboard overview for current tenant

    Returns:
    - Total reports count
    - Total brands count
    - Active feeds count
    - Sentiment distribution
    - Top sources
    """
    # Count total reports for tenant
    total_reports = db.query(func.count(Report.id)).filter(
        Report.tenant_id == current_user.tenant_id
    ).scalar() or 0

    # Count total brands for tenant
    total_brands = db.query(func.count(BrandConfig.id)).filter(
        BrandConfig.tenant_id == current_user.tenant_id
    ).scalar() or 0

    # Count active feeds for tenant
    active_feeds = db.query(func.count(FeedConfig.id)).filter(
        FeedConfig.tenant_id == current_user.tenant_id,
        FeedConfig.enabled == True
    ).scalar() or 0

    # Get sentiment distribution for tenant
    sentiment_dist = db.query(
        Report.sentiment,
        func.count(Report.id).label('count')
    ).filter(
        Report.tenant_id == current_user.tenant_id
    ).group_by(Report.sentiment).all()

    sentiment_distribution = [
        {"sentiment": s[0], "count": s[1]}
        for s in sentiment_dist
    ]

    # Get top sources for tenant
    top_sources = db.query(
        Report.source,
        func.count(Report.id).label('count')
    ).filter(
        Report.tenant_id == current_user.tenant_id
    ).group_by(Report.source).order_by(desc('count')).limit(5).all()

    top_sources_list = [
        {"source": s[0], "count": s[1]}
        for s in top_sources
    ]

    return {
        "total_reports": total_reports,
        "total_brands": total_brands,
        "active_feeds": active_feeds,
        "sentiment_distribution": sentiment_distribution,
        "top_sources": top_sources_list
    }


@router.get("/reports/recent")
async def get_recent_reports(
    limit: int = Query(10, ge=1, le=50),
    skip: int = Query(0, ge=0),
    source_type: str = Query(None, description="Filter by source type: social, digital, or broadcast"),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Get recent reports for current tenant with pagination, optionally filtered by source_type

    Returns:
    - Total count and paginated list of most recent reports
    """
    # Build base query
    query = db.query(Report).filter(Report.tenant_id == current_user.tenant_id)

    # Apply source_type filter if provided
    if source_type:
        query = query.filter(Report.source_type == source_type)

    # Get total count
    total = query.count()

    # Get paginated reports
    reports = query.order_by(desc(Report.timestamp)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": str(report.id),
                "title": report.title,
                "source": report.source,
                "provider": report.provider,
                "source_type": report.source_type,
                "timestamp": report.timestamp.isoformat() if report.timestamp else None,
                "summary": report.summary,
                "brands": report.brands or [],
                "sentiment": report.sentiment,
                "link": report.link,
                "est_reach": report.est_reach or 0,
                "created_at": report.created_at.isoformat() if report.created_at else None
            }
            for report in reports
        ]
    }


@router.get("/brands/top")
async def get_top_brands(
    limit: int = Query(10, ge=1, le=50),
    skip: int = Query(0, ge=0),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Get top brands by mention count for current tenant with pagination

    Returns:
    - Total count and paginated list of top brands
    """
    # Get total count
    total = db.query(func.count(BrandConfig.id)).filter(
        BrandConfig.tenant_id == current_user.tenant_id
    ).scalar() or 0

    # Get paginated brands
    brands = db.query(BrandConfig).filter(
        BrandConfig.tenant_id == current_user.tenant_id
    ).order_by(desc(BrandConfig.mention_count)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": str(brand.id),
                "brand_name": brand.brand_name,
                "mention_count": brand.mention_count,
                "is_known_brand": brand.is_known_brand,
                "created_at": brand.created_at.isoformat() if brand.created_at else None
            }
            for brand in brands
        ]
    }
