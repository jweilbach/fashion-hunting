"""
Feed Configuration model
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class FeedConfig(Base):
    """Feed configuration for content sources"""
    __tablename__ = 'feed_configs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)

    # Feed details
    provider = Column(String(50), nullable=False, index=True)  # RSS, TikTok, Instagram
    feed_type = Column(String(50))  # hashtag, keyword, user, rss_url
    feed_value = Column(Text, nullable=False)  # The actual URL, hashtag, username

    # Configuration
    enabled = Column(Boolean, default=True, index=True)
    fetch_count = Column(Integer, default=30)
    config = Column(JSONB, default=dict)

    # Metadata
    label = Column(String(255))
    last_fetched = Column(DateTime(timezone=True))
    last_error = Column(Text)
    fetch_count_success = Column(Integer, default=0)
    fetch_count_failed = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="feed_configs")

    def __repr__(self):
        return f"<FeedConfig(provider='{self.provider}', label='{self.label}', enabled={self.enabled})>"

    def to_dict(self):
        """Convert feed config to dictionary"""
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'provider': self.provider,
            'feed_type': self.feed_type,
            'feed_value': self.feed_value,
            'enabled': self.enabled,
            'fetch_count': self.fetch_count,
            'config': self.config,
            'label': self.label,
            'last_fetched': self.last_fetched.isoformat() if self.last_fetched else None,
            'last_error': self.last_error,
            'fetch_count_success': self.fetch_count_success,
            'fetch_count_failed': self.fetch_count_failed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
