"""
Analytics Cache model for dashboard performance
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class AnalyticsCache(Base):
    """Cached analytics data for dashboard performance"""
    __tablename__ = 'analytics_cache'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)

    # Cache metadata
    metric_type = Column(String(100), nullable=False)  # daily_mentions, sentiment_trend, top_brands
    time_period = Column(String(50), nullable=False)  # today, week, month, year
    filters = Column(JSONB, default=dict)  # Additional filter context

    # Cached data
    data = Column(JSONB, nullable=False)

    # Cache management
    cached_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Constraints
    __table_args__ = (
        Index(
            'idx_analytics_cache_unique',
            'tenant_id', 'metric_type', 'time_period', 'filters',
            unique=True
        ),
    )

    def __repr__(self):
        return f"<AnalyticsCache(metric='{self.metric_type}', period='{self.time_period}')>"

    def to_dict(self):
        """Convert analytics cache to dictionary"""
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'metric_type': self.metric_type,
            'time_period': self.time_period,
            'filters': self.filters,
            'data': self.data,
            'cached_at': self.cached_at.isoformat() if self.cached_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }

    @property
    def is_expired(self) -> bool:
        """Check if cache is expired"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > self.expires_at
