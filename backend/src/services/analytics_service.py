"""
Analytics Service
Handles business logic for analytics and insights
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session

from repositories.report_repository import ReportRepository
from repositories.brand_repository import BrandRepository


class AnalyticsService:
    """Service for analytics and insights generation"""

    def __init__(
        self,
        db: Session,
        report_repo: Optional[ReportRepository] = None,
        brand_repo: Optional[BrandRepository] = None
    ):
        self.db = db
        self.report_repo = report_repo or ReportRepository(db)
        self.brand_repo = brand_repo or BrandRepository(db)

    def get_sentiment_analysis(self, tenant_id: UUID, days: int = 30) -> Dict[str, Any]:
        """
        Get sentiment analysis with percentages

        Args:
            tenant_id: UUID of the tenant
            days: Number of days to analyze

        Returns:
            Dict with sentiment stats and percentages
        """
        sentiment_stats = self.report_repo.get_sentiment_stats(tenant_id, days=days)

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

    def get_top_brands(
        self, tenant_id: UUID, days: int = 30, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top mentioned brands with rankings

        Args:
            tenant_id: UUID of the tenant
            days: Number of days to analyze
            limit: Number of top brands to return

        Returns:
            List of brands with mention counts and rankings
        """
        top_brands = self.report_repo.get_top_brands(tenant_id, days=days, limit=limit)

        return [
            {
                "brand": brand,
                "mention_count": count,
                "rank": idx + 1
            }
            for idx, (brand, count) in enumerate(top_brands)
        ]

    def get_daily_report_counts(
        self,
        tenant_id: UUID,
        days: int = 30,
        provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily report counts with formatted data

        Args:
            tenant_id: UUID of the tenant
            days: Number of days to analyze
            provider: Optional provider filter

        Returns:
            List of daily stats with formatted dates
        """
        daily_stats = self.report_repo.get_daily_counts(
            tenant_id, days=days, provider=provider
        )

        return [
            {
                "date": date.isoformat(),
                "report_count": count,
                "avg_reach": avg_reach or 0,
                "provider": provider or "all"
            }
            for date, count, avg_reach in daily_stats
        ]

    def get_provider_breakdown(self, tenant_id: UUID, days: int = 30) -> Dict[str, Any]:
        """
        Get provider breakdown with percentages

        Args:
            tenant_id: UUID of the tenant
            days: Number of days to analyze

        Returns:
            Dict with provider stats and percentages
        """
        provider_stats = self.report_repo.get_provider_stats(tenant_id, days=days)

        total_reports = sum(stat['report_count'] for stat in provider_stats.values())
        total_reach = sum(stat['total_reach'] for stat in provider_stats.values())

        # Add percentages
        for provider, stats in provider_stats.items():
            stats['report_percentage'] = (
                round((stats['report_count'] / total_reports * 100), 2)
                if total_reports > 0 else 0
            )
            stats['reach_percentage'] = (
                round((stats['total_reach'] / total_reach * 100), 2)
                if total_reach > 0 else 0
            )

        return {
            "period_days": days,
            "total_reports": total_reports,
            "total_reach": total_reach,
            "providers": provider_stats,
            "start_date": (datetime.now() - timedelta(days=days)).isoformat(),
            "end_date": datetime.now().isoformat()
        }

    def get_analytics_summary(self, tenant_id: UUID, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive analytics summary

        Args:
            tenant_id: UUID of the tenant
            days: Number of days to analyze

        Returns:
            Dict with comprehensive analytics
        """
        # Get all analytics
        sentiment_stats = self.report_repo.get_sentiment_stats(tenant_id, days=days)
        top_brands = self.report_repo.get_top_brands(tenant_id, days=days, limit=5)
        provider_stats = self.report_repo.get_provider_stats(tenant_id, days=days)

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
                    sentiment: round((count / total_reports * 100), 2)
                    if total_reports > 0 else 0
                    for sentiment, count in sentiment_stats.items()
                }
            },
            "top_brands": [
                {"brand": brand, "mentions": count}
                for brand, count in top_brands
            ],
            "providers": provider_stats
        }

    def get_trends(self, tenant_id: UUID) -> Dict[str, Any]:
        """
        Get trending insights comparing current week vs previous week

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Dict with trend analysis
        """
        # Current week (last 7 days)
        current_sentiment = self.report_repo.get_sentiment_stats(tenant_id, days=7)
        current_total = sum(current_sentiment.values())

        # Previous week (8-14 days ago)
        # Note: This is an approximation using 14-day stats
        prev_sentiment = self.report_repo.get_sentiment_stats(tenant_id, days=14)
        prev_total = sum(prev_sentiment.values()) - current_total

        # Calculate change
        volume_change = current_total - prev_total
        volume_change_pct = (
            round((volume_change / prev_total * 100), 2)
            if prev_total > 0 else 0
        )

        # Get current top brands
        current_brands = self.report_repo.get_top_brands(tenant_id, days=7, limit=10)

        # Determine trend direction
        if volume_change > 0:
            trend = "up"
        elif volume_change < 0:
            trend = "down"
        else:
            trend = "stable"

        return {
            "period": "last_7_days_vs_previous_7_days",
            "current_week": {
                "total_reports": current_total,
                "sentiment": current_sentiment
            },
            "previous_week": {
                "total_reports": prev_total,
                "sentiment": {
                    k: v - current_sentiment.get(k, 0)
                    for k, v in prev_sentiment.items()
                }
            },
            "changes": {
                "volume_change": volume_change,
                "volume_change_percentage": volume_change_pct,
                "trend": trend
            },
            "top_brands_current_week": [
                {"brand": brand, "mentions": count}
                for brand, count in current_brands
            ]
        }

    def get_brand_analytics(
        self, tenant_id: UUID, brand_name: str, days: int = 30
    ) -> Dict[str, Any]:
        """
        Get analytics for a specific brand

        Args:
            tenant_id: UUID of the tenant
            brand_name: Name of the brand to analyze
            days: Number of days to analyze

        Returns:
            Dict with brand-specific analytics
        """
        # Get reports mentioning this brand - use database filtering instead of Python
        # This is much more efficient than loading all reports and filtering
        start_date = datetime.now() - timedelta(days=days)

        # First get count of reports in time period for limit calculation
        all_reports_count = self.report_repo.count(
            tenant_id=tenant_id,
            start_date=start_date
        )

        # Use get_by_brand which filters at database level
        brand_reports = self.report_repo.get_by_brand(
            tenant_id=tenant_id,
            brand_name=brand_name,
            limit=min(all_reports_count, 10000)  # Reasonable upper limit
        )

        # Further filter by date range if needed (get_by_brand doesn't have date filter)
        brand_reports = [r for r in brand_reports if r.timestamp >= start_date]

        # Calculate sentiment distribution
        sentiment_counts = {}
        for report in brand_reports:
            sentiment = report.sentiment or 'neutral'
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

        total = len(brand_reports)
        sentiment_percentages = {
            sentiment: round((count / total * 100), 2) if total > 0 else 0
            for sentiment, count in sentiment_counts.items()
        }

        # Calculate total reach
        total_reach = sum(
            (r.estimated_reach or 0) for r in brand_reports
        )

        # Get provider breakdown
        provider_counts = {}
        for report in brand_reports:
            provider = report.provider or 'unknown'
            provider_counts[provider] = provider_counts.get(provider, 0) + 1

        return {
            "brand": brand_name,
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": datetime.now().isoformat(),
            "total_mentions": total,
            "total_estimated_reach": total_reach,
            "avg_daily_mentions": round(total / days, 2) if days > 0 else 0,
            "sentiment": {
                "counts": sentiment_counts,
                "percentages": sentiment_percentages
            },
            "providers": provider_counts
        }
