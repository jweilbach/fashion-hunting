"""
Feed Config repository for database operations
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from uuid import UUID

from models.feed import FeedConfig


class FeedRepository:
    """Repository for FeedConfig operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, feed_id: UUID) -> Optional[FeedConfig]:
        """Get feed config by ID"""
        return self.db.query(FeedConfig).filter(FeedConfig.id == feed_id).first()

    def get_all(
        self,
        tenant_id: UUID,
        provider: Optional[str] = None,
        enabled_only: bool = False,
    ) -> List[FeedConfig]:
        """Get all feed configs for a tenant"""
        query = self.db.query(FeedConfig).filter(FeedConfig.tenant_id == tenant_id)

        if provider:
            query = query.filter(FeedConfig.provider == provider)

        if enabled_only:
            query = query.filter(FeedConfig.enabled == True)

        return query.all()

    def get_enabled(self, tenant_id: UUID) -> List[FeedConfig]:
        """Get all enabled feed configs"""
        return self.get_all(tenant_id, enabled_only=True)

    def get_active(self, tenant_id: UUID) -> List[FeedConfig]:
        """Get all active feed configs (alias for enabled)"""
        return self.db.query(FeedConfig).filter(
            FeedConfig.tenant_id == tenant_id,
            FeedConfig.is_active == True
        ).all()

    def get_inactive(self, tenant_id: UUID) -> List[FeedConfig]:
        """Get all inactive feed configs"""
        return self.db.query(FeedConfig).filter(
            FeedConfig.tenant_id == tenant_id,
            FeedConfig.is_active == False
        ).all()

    def get_by_type(self, tenant_id: UUID, feed_type: str) -> List[FeedConfig]:
        """Get feed configs by type"""
        return self.db.query(FeedConfig).filter(
            FeedConfig.tenant_id == tenant_id,
            FeedConfig.feed_type == feed_type
        ).all()

    def get_by_type_and_status(self, tenant_id: UUID, feed_type: str, is_active: bool) -> List[FeedConfig]:
        """Get feed configs by type and active status"""
        return self.db.query(FeedConfig).filter(
            FeedConfig.tenant_id == tenant_id,
            FeedConfig.feed_type == feed_type,
            FeedConfig.is_active == is_active
        ).all()

    def create(self, **kwargs) -> FeedConfig:
        """Create a new feed config"""
        feed = FeedConfig(**kwargs)
        self.db.add(feed)
        self.db.commit()
        self.db.refresh(feed)
        return feed

    def update(self, feed_id: UUID, **kwargs) -> Optional[FeedConfig]:
        """Update a feed config"""
        feed = self.get_by_id(feed_id)
        if feed:
            for key, value in kwargs.items():
                setattr(feed, key, value)
            self.db.commit()
            self.db.refresh(feed)
        return feed

    def delete(self, feed_id: UUID) -> bool:
        """Delete a feed config"""
        feed = self.get_by_id(feed_id)
        if feed:
            self.db.delete(feed)
            self.db.commit()
            return True
        return False

    def mark_fetched(
        self, feed_id: UUID, success: bool = True, error: Optional[str] = None
    ) -> Optional[FeedConfig]:
        """Mark a feed as fetched and update stats"""
        feed = self.get_by_id(feed_id)
        if feed:
            feed.last_fetched = datetime.now()

            if success:
                feed.fetch_count_success += 1
                feed.last_error = None
            else:
                feed.fetch_count_failed += 1
                feed.last_error = error

            self.db.commit()
            self.db.refresh(feed)
        return feed

    def enable(self, feed_id: UUID) -> Optional[FeedConfig]:
        """Enable a feed"""
        return self.update(feed_id, enabled=True)

    def disable(self, feed_id: UUID) -> Optional[FeedConfig]:
        """Disable a feed"""
        return self.update(feed_id, enabled=False)
