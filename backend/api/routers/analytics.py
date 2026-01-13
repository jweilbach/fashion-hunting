"""
Analytics Router
Provides analytics and insights from media reports
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api.database import get_db
from api import schemas
from api.auth import get_current_user, require_viewer
from models.user import User
from services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/sentiment", response_model=Dict[str, Any])
async def get_sentiment_analysis(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Get sentiment analysis breakdown for reports

    - **days**: Number of days to analyze (default: 30, max: 365)

    Returns:
    - Sentiment distribution (positive, neutral, negative)
    - Total reports analyzed
    - Time period
    """
    service = AnalyticsService(db)
    return service.get_sentiment_analysis(current_user.tenant_id, days=days)


@router.get("/brands/top", response_model=List[Dict[str, Any]])
async def get_top_brands(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Number of top brands to return"),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Get top mentioned brands

    - **days**: Number of days to analyze (default: 30)
    - **limit**: Number of top brands to return (default: 10, max: 50)

    Returns:
    - List of brands with mention counts
    - Sorted by frequency (descending)
    """
    service = AnalyticsService(db)
    return service.get_top_brands(current_user.tenant_id, days=days, limit=limit)


@router.get("/reports/daily", response_model=List[Dict[str, Any]])
async def get_daily_report_counts(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Get daily report counts over time

    - **days**: Number of days to analyze (default: 30)
    - **provider**: Optional filter by provider (RSS, TikTok, etc.)

    Returns:
    - Daily report counts
    - Total reports per day
    - Average reach per day
    """
    service = AnalyticsService(db)
    return service.get_daily_report_counts(
        current_user.tenant_id, days=days, provider=provider
    )


@router.get("/providers", response_model=Dict[str, Any])
async def get_provider_breakdown(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Get breakdown of reports by provider

    - **days**: Number of days to analyze (default: 30)

    Returns:
    - Report counts by provider
    - Total reach by provider
    - Percentage distribution
    """
    service = AnalyticsService(db)
    return service.get_provider_breakdown(current_user.tenant_id, days=days)


@router.get("/summary", response_model=Dict[str, Any])
async def get_analytics_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics summary

    - **days**: Number of days to analyze (default: 30)

    Returns:
    - Total reports
    - Sentiment breakdown
    - Top 5 brands
    - Provider breakdown
    - Average daily reports
    - Total estimated reach
    """
    service = AnalyticsService(db)
    return service.get_analytics_summary(current_user.tenant_id, days=days)


@router.get("/trends", response_model=Dict[str, Any])
async def get_trends(
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    Get trending insights and comparisons

    Compares current week vs previous week metrics:
    - Report volume change
    - Sentiment shifts
    - New brands emerging
    - Provider performance changes
    """
    service = AnalyticsService(db)
    return service.get_trends(current_user.tenant_id)
