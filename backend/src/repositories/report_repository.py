"""
Report repository for database operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func
from uuid import UUID

from models.report import Report


class ReportRepository:
    """Repository for Report operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, report_id: UUID) -> Optional[Report]:
        """Get report by ID"""
        return self.db.query(Report).filter(Report.id == report_id).first()

    def get_by_link(self, tenant_id: UUID, link: str) -> Optional[Report]:
        """Get report by link (for deduplication)"""
        return (
            self.db.query(Report)
            .filter(Report.tenant_id == tenant_id, Report.link == link)
            .first()
        )

    def get_all(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        provider: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sentiment: Optional[str] = None,
        brand: Optional[str] = None,
    ) -> List[Report]:
        """Get all reports with filters and pagination"""
        query = self.db.query(Report).filter(Report.tenant_id == tenant_id)

        if provider:
            query = query.filter(Report.provider == provider)

        if status:
            query = query.filter(Report.processing_status == status)

        if start_date:
            query = query.filter(Report.timestamp >= start_date)

        if end_date:
            query = query.filter(Report.timestamp <= end_date)

        if sentiment:
            query = query.filter(Report.sentiment == sentiment)

        if brand:
            query = query.filter(Report.brands.contains([brand]))

        return query.order_by(desc(Report.timestamp)).offset(skip).limit(limit).all()

    def get_recent(
        self, tenant_id: UUID, days: int = 7, limit: int = 100
    ) -> List[Report]:
        """Get recent reports from the last N days"""
        cutoff = datetime.now() - timedelta(days=days)
        return (
            self.db.query(Report)
            .filter(
                Report.tenant_id == tenant_id,
                Report.timestamp >= cutoff,
                Report.processing_status == 'completed'
            )
            .order_by(desc(Report.timestamp))
            .limit(limit)
            .all()
        )

    def get_by_brand(
        self, tenant_id: UUID, brand_name: str, limit: int = 100
    ) -> List[Report]:
        """Get reports mentioning a specific brand"""
        return (
            self.db.query(Report)
            .filter(
                Report.tenant_id == tenant_id,
                Report.brands.contains([brand_name]),  # Array contains
                Report.processing_status == 'completed'
            )
            .order_by(desc(Report.timestamp))
            .limit(limit)
            .all()
        )

    def search(
        self, tenant_id: UUID, query: str, limit: int = 100
    ) -> List[Report]:
        """Full-text search on title and summary"""
        search_term = f"%{query}%"
        return (
            self.db.query(Report)
            .filter(
                Report.tenant_id == tenant_id,
                or_(
                    Report.title.ilike(search_term),
                    Report.summary.ilike(search_term)
                )
            )
            .order_by(desc(Report.timestamp))
            .limit(limit)
            .all()
        )

    def create(self, **kwargs) -> Report:
        """Create a new report"""
        report = Report(**kwargs)
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def bulk_create(self, reports: List[Dict[str, Any]]) -> List[Report]:
        """Bulk create reports"""
        report_objects = [Report(**report_data) for report_data in reports]
        self.db.bulk_save_objects(report_objects)
        self.db.commit()
        return report_objects

    def update(self, report_id: UUID, **kwargs) -> Optional[Report]:
        """Update a report"""
        report = self.get_by_id(report_id)
        if report:
            for key, value in kwargs.items():
                setattr(report, key, value)
            self.db.commit()
            self.db.refresh(report)
        return report

    def delete(self, report_id: UUID) -> bool:
        """Delete a report"""
        report = self.get_by_id(report_id)
        if report:
            self.db.delete(report)
            self.db.commit()
            return True
        return False

    def count(
        self,
        tenant_id: UUID,
        provider: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sentiment: Optional[str] = None,
        brand: Optional[str] = None,
    ) -> int:
        """Count reports with filters"""
        query = self.db.query(func.count(Report.id)).filter(Report.tenant_id == tenant_id)

        if provider:
            query = query.filter(Report.provider == provider)

        if status:
            query = query.filter(Report.processing_status == status)

        if start_date:
            query = query.filter(Report.timestamp >= start_date)

        if end_date:
            query = query.filter(Report.timestamp <= end_date)

        if sentiment:
            query = query.filter(Report.sentiment == sentiment)

        if brand:
            query = query.filter(Report.brands.contains([brand]))

        return query.scalar() or 0

    # Analytics methods

    def get_sentiment_stats(self, tenant_id: UUID, days: int = 30) -> Dict[str, int]:
        """Get sentiment breakdown for recent reports"""
        cutoff = datetime.now() - timedelta(days=days)
        results = (
            self.db.query(Report.sentiment, func.count(Report.id))
            .filter(
                Report.tenant_id == tenant_id,
                Report.timestamp >= cutoff,
                Report.processing_status == 'completed'
            )
            .group_by(Report.sentiment)
            .all()
        )

        return {sentiment or 'unknown': count for sentiment, count in results}

    def get_provider_stats(self, tenant_id: UUID, days: int = 30) -> Dict[str, Dict[str, int]]:
        """Get provider breakdown for recent reports"""
        cutoff = datetime.now() - timedelta(days=days)
        results = (
            self.db.query(
                Report.provider,
                func.count(Report.id).label('count'),
                func.sum(Report.est_reach).label('total_reach')
            )
            .filter(
                Report.tenant_id == tenant_id,
                Report.timestamp >= cutoff,
                Report.processing_status == 'completed'
            )
            .group_by(Report.provider)
            .all()
        )

        return {
            provider: {
                'report_count': count,
                'total_reach': total_reach or 0
            }
            for provider, count, total_reach in results
        }

    def get_daily_counts(
        self, tenant_id: UUID, days: int = 30, provider: Optional[str] = None
    ) -> List[tuple]:
        """Get daily report counts with average reach"""
        cutoff = datetime.now() - timedelta(days=days)
        query = (
            self.db.query(
                func.date(Report.timestamp).label('date'),
                func.count(Report.id).label('count'),
                func.avg(Report.est_reach).label('avg_reach')
            )
            .filter(
                Report.tenant_id == tenant_id,
                Report.timestamp >= cutoff,
                Report.processing_status == 'completed'
            )
        )

        if provider:
            query = query.filter(Report.provider == provider)

        results = (
            query
            .group_by(func.date(Report.timestamp))
            .order_by(func.date(Report.timestamp))
            .all()
        )

        return [(date, count, avg_reach) for date, count, avg_reach in results]

    def get_top_brands(
        self, tenant_id: UUID, days: int = 30, limit: int = 10
    ) -> List[tuple]:
        """Get top mentioned brands - returns list of (brand, count) tuples"""
        cutoff = datetime.now() - timedelta(days=days)

        # Use unnest to expand brand arrays and count occurrences
        results = (
            self.db.query(
                func.unnest(Report.brands).label('brand'),
                func.count().label('mentions')
            )
            .filter(
                Report.tenant_id == tenant_id,
                Report.timestamp >= cutoff,
                Report.processing_status == 'completed'
            )
            .group_by(func.unnest(Report.brands))
            .order_by(desc(func.count()))
            .limit(limit)
            .all()
        )

        return [(brand, mentions) for brand, mentions in results]
