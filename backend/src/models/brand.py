"""
Brand Configuration model
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class BrandConfig(Base):
    """Brand configuration and tracking"""
    __tablename__ = 'brand_configs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)

    # Brand details
    brand_name = Column(String(255), nullable=False)
    aliases = Column(ARRAY(Text), default=list)

    # Filtering
    is_known_brand = Column(Boolean, default=True, index=True)
    should_ignore = Column(Boolean, default=False)

    # Metadata
    category = Column(String(100))  # client, competitor, industry
    notes = Column(Text)

    # Social media profiles configuration (Brand 360)
    social_profiles = Column(JSONB, default=dict)  # Flexible per-provider config

    # Stats (denormalized for performance)
    mention_count = Column(Integer, default=0)
    last_mentioned = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="brand_configs")

    # Constraints
    __table_args__ = (
        Index('idx_brand_configs_tenant_brand', 'tenant_id', 'brand_name', unique=True),
        Index('idx_brand_configs_tenant_known', 'tenant_id', 'is_known_brand'),
    )

    def __repr__(self):
        return f"<BrandConfig(brand_name='{self.brand_name}', category='{self.category}', known={self.is_known_brand})>"

    def to_dict(self):
        """Convert brand config to dictionary"""
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'brand_name': self.brand_name,
            'aliases': self.aliases or [],
            'is_known_brand': self.is_known_brand,
            'should_ignore': self.should_ignore,
            'category': self.category,
            'notes': self.notes,
            'social_profiles': self.social_profiles or {},
            'mention_count': self.mention_count,
            'last_mentioned': self.last_mentioned.isoformat() if self.last_mentioned else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
