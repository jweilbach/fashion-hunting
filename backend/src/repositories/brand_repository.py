"""
Brand Config repository for database operations
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from uuid import UUID

from models.brand import BrandConfig


class BrandRepository:
    """Repository for BrandConfig operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, brand_id: UUID) -> Optional[BrandConfig]:
        """Get brand config by ID"""
        return self.db.query(BrandConfig).filter(BrandConfig.id == brand_id).first()

    def get_by_name(self, tenant_id: UUID, brand_name: str) -> Optional[BrandConfig]:
        """Get brand config by name"""
        return (
            self.db.query(BrandConfig)
            .filter(
                BrandConfig.tenant_id == tenant_id,
                BrandConfig.brand_name == brand_name
            )
            .first()
        )

    def get_all(
        self,
        tenant_id: UUID,
        known_only: bool = False,
        category: Optional[str] = None,
    ) -> List[BrandConfig]:
        """Get all brand configs for a tenant"""
        query = self.db.query(BrandConfig).filter(BrandConfig.tenant_id == tenant_id)

        if known_only:
            query = query.filter(BrandConfig.is_known_brand == True)

        if category:
            query = query.filter(BrandConfig.category == category)

        return query.order_by(desc(BrandConfig.mention_count)).all()

    def get_known_brands(self, tenant_id: UUID) -> List[BrandConfig]:
        """Get all known brands"""
        return self.get_all(tenant_id, known_only=True)

    def get_ignored_brands(self, tenant_id: UUID) -> List[BrandConfig]:
        """Get all ignored brands"""
        return (
            self.db.query(BrandConfig)
            .filter(
                BrandConfig.tenant_id == tenant_id,
                BrandConfig.should_ignore == True
            )
            .all()
        )

    def create(self, **kwargs) -> BrandConfig:
        """Create a new brand config"""
        brand = BrandConfig(**kwargs)
        self.db.add(brand)
        self.db.commit()
        self.db.refresh(brand)
        return brand

    def get_or_create(self, tenant_id: UUID, brand_name: str, **kwargs) -> BrandConfig:
        """Get or create a brand config"""
        brand = self.get_by_name(tenant_id, brand_name)

        if not brand:
            brand = self.create(
                tenant_id=tenant_id,
                brand_name=brand_name,
                **kwargs
            )

        return brand

    def update(self, brand_id: UUID, **kwargs) -> Optional[BrandConfig]:
        """Update a brand config"""
        brand = self.get_by_id(brand_id)
        if brand:
            for key, value in kwargs.items():
                setattr(brand, key, value)
            self.db.commit()
            self.db.refresh(brand)
        return brand

    def delete(self, brand_id: UUID) -> bool:
        """Delete a brand config"""
        brand = self.get_by_id(brand_id)
        if brand:
            self.db.delete(brand)
            self.db.commit()
            return True
        return False

    def increment_mention_count(
        self, tenant_id: UUID, brand_name: str, timestamp: datetime
    ) -> Optional[BrandConfig]:
        """Increment mention count for a brand"""
        brand = self.get_by_name(tenant_id, brand_name)

        if brand:
            brand.mention_count += 1

            # Update last_mentioned if this is newer
            if not brand.last_mentioned or timestamp > brand.last_mentioned:
                brand.last_mentioned = timestamp

            self.db.commit()
            self.db.refresh(brand)

        return brand

    def is_ignored(self, tenant_id: UUID, brand_name: str) -> bool:
        """Check if a brand should be ignored"""
        brand = self.get_by_name(tenant_id, brand_name)
        return brand.should_ignore if brand else False

    def is_known(self, tenant_id: UUID, brand_name: str) -> bool:
        """Check if a brand is known"""
        brand = self.get_by_name(tenant_id, brand_name)
        return brand.is_known_brand if brand else False
