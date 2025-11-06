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
from repositories.report_repository import ReportRepository

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
    repo = ReportRepository(db)
    sentiment_stats = repo.get_sentiment_stats(current_user.tenant_id, days=days)

    total = sum(sentiment_stats.values())
    percentages = {
        sentiment: round((count / total * 100), 2) if total > 0 else 0
        for sentiment, count in sentiment_stats.items()
    }

    return {
        "period_days": days,
        "total_reports": total,
        "sentiment_counts": sentiment_stats,
        "sentiment_percentages": percentages,
        "start_date": (datetime.now() - timedelta(days=days)).isoformat(),
        "end_date": datetime.now().isoformat()
    }


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
    repo = ReportRepository(db)
    top_brands = repo.get_top_brands(current_user.tenant_id, days=days, limit=limit)

    return [
        {
            "brand": brand,
            "mention_count": count,
            "rank": idx + 1
        }
        for idx, (brand, count) in enumerate(top_brands)
    ]


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
    repo = ReportRepository(db)
    daily_stats = repo.get_daily_counts(current_user.tenant_id, days=days, provider=provider)

    return [
        {
            "date": date.isoformat(),
            "report_count": count,
            "avg_reach": avg_reach or 0,
            "provider": provider or "all"
        }
        for date, count, avg_reach in daily_stats
    ]


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
    repo = ReportRepository(db)
    provider_stats = repo.get_provider_stats(current_user.tenant_id, days=days)

    total_reports = sum(stat['report_count'] for stat in provider_stats.values())
    total_reach = sum(stat['total_reach'] for stat in provider_stats.values())

    # Add percentages
    for provider, stats in provider_stats.items():
        stats['report_percentage'] = round((stats['report_count'] / total_reports * 100), 2) if total_reports > 0 else 0
        stats['reach_percentage'] = round((stats['total_reach'] / total_reach * 100), 2) if total_reach > 0 else 0

    return {
        "period_days": days,
        "total_reports": total_reports,
        "total_reach": total_reach,
        "providers": provider_stats,
        "start_date": (datetime.now() - timedelta(days=days)).isoformat(),
        "end_date": datetime.now().isoformat()
    }


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
    repo = ReportRepository(db)

    # Get all analytics
    sentiment_stats = repo.get_sentiment_stats(current_user.tenant_id, days=days)
    top_brands = repo.get_top_brands(current_user.tenant_id, days=days, limit=5)
    provider_stats = repo.get_provider_stats(current_user.tenant_id, days=days)

    total_reports = sum(sentiment_stats.values())
    total_reach = sum(stat['total_reach'] for stat in provider_stats.values())
    avg_daily_reports = round(total_reports / days, 2) if days > 0 else 0

    return {
        "period_days": days,
        "start_date": (datetime.now() - timedelta(days=days)).isoformat(),
        "end_date": datetime.now().isoformat(),
        "total_reports": total_reports,
        "avg_daily_reports": avg_daily_reports,
        "total_estimated_reach": total_reach,
        "sentiment": {
            "counts": sentiment_stats,
            "percentages": {
                sentiment: round((count / total_reports * 100), 2) if total_reports > 0 else 0
                for sentiment, count in sentiment_stats.items()
            }
        },
        "top_brands": [
            {"brand": brand, "mentions": count}
            for brand, count in top_brands
        ],
        "providers": provider_stats
    }


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
    repo = ReportRepository(db)

    # Current week (last 7 days)
    current_sentiment = repo.get_sentiment_stats(current_user.tenant_id, days=7)
    current_total = sum(current_sentiment.values())

    # Previous week (8-14 days ago)
    # Note: This would require date range filtering in repository methods
    # For now, we'll use 14-day stats and approximate
    prev_sentiment = repo.get_sentiment_stats(current_user.tenant_id, days=14)
    prev_total = sum(prev_sentiment.values()) - current_total

    # Calculate change
    volume_change = current_total - prev_total
    volume_change_pct = round((volume_change / prev_total * 100), 2) if prev_total > 0 else 0

    # Get current top brands
    current_brands = repo.get_top_brands(current_user.tenant_id, days=7, limit=10)

    return {
        "period": "last_7_days_vs_previous_7_days",
        "current_week": {
            "total_reports": current_total,
            "sentiment": current_sentiment
        },
        "previous_week": {
            "total_reports": prev_total,
            "sentiment": {k: v - current_sentiment.get(k, 0) for k, v in prev_sentiment.items()}
        },
        "changes": {
            "volume_change": volume_change,
            "volume_change_percentage": volume_change_pct,
            "trend": "up" if volume_change > 0 else "down" if volume_change < 0 else "stable"
        },
        "top_brands_current_week": [
            {"brand": brand, "mentions": count}
            for brand, count in current_brands
        ]
    }
