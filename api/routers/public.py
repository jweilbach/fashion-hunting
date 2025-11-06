"""
Public Router - Unauthenticated endpoints for dashboard
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
from models.report import Report
from models.brand import BrandConfig
from models.feed import FeedConfig

router = APIRouter()


@router.get("/overview")
async def get_overview(db: Session = Depends(get_db)):
    """
    Get dashboard overview - public endpoint (no auth required)

    Returns:
    - Total reports count
    - Total brands count
    - Active feeds count
    - Sentiment distribution
    - Top sources
    """
    # Count total reports
    total_reports = db.query(func.count(Report.id)).scalar() or 0

    # Count total brands
    total_brands = db.query(func.count(BrandConfig.id)).scalar() or 0

    # Count active feeds
    active_feeds = db.query(func.count(FeedConfig.id)).filter(FeedConfig.enabled == True).scalar() or 0

    # Get sentiment distribution
    sentiment_dist = db.query(
        Report.sentiment,
        func.count(Report.id).label('count')
    ).group_by(Report.sentiment).all()

    sentiment_distribution = [
        {"sentiment": s[0], "count": s[1]}
        for s in sentiment_dist
    ]

    # Get top sources
    top_sources = db.query(
        Report.source,
        func.count(Report.id).label('count')
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
    db: Session = Depends(get_db)
):
    """
    Get recent reports - public endpoint (no auth required)

    Returns:
    - List of most recent reports
    """
    reports = db.query(Report).order_by(desc(Report.timestamp)).limit(limit).all()

    return [
        {
            "id": str(report.id),
            "title": report.title,
            "source": report.source,
            "provider": report.provider,
            "timestamp": report.timestamp.isoformat() if report.timestamp else None,
            "summary": report.summary,
            "brands": report.brands or [],
            "sentiment": report.sentiment,
            "link": report.link,
            "est_reach": report.est_reach or 0
        }
        for report in reports
    ]


@router.get("/brands/top")
async def get_top_brands(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get top brands by mention count - public endpoint (no auth required)

    Returns:
    - List of top brands
    """
    brands = db.query(BrandConfig).order_by(desc(BrandConfig.mention_count)).limit(limit).all()

    return [
        {
            "id": str(brand.id),
            "brand_name": brand.brand_name,
            "mention_count": brand.mention_count,
            "is_known_brand": brand.is_known_brand,
            "created_at": brand.created_at.isoformat() if brand.created_at else None
        }
        for brand in brands
    ]
