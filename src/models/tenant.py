"""
Tenant and Provider Credential models
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class Tenant(Base):
    """Multi-tenant account model"""
    __tablename__ = 'tenants'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)

    # Contact info
    email = Column(String(255), unique=True, nullable=False, index=True)
    company_name = Column(String(255))

    # Configuration
    settings = Column(JSONB, default=dict)
    rate_limit_config = Column(JSONB, default={
        "openai_rpm": 15,
        "fetch_concurrency": 5
    })

    # Subscription/billing
    plan = Column(String(50), default='free')
    status = Column(String(50), default='active', index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_report_run = Column(DateTime(timezone=True))

    # Relationships
    reports = relationship("Report", back_populates="tenant", cascade="all, delete-orphan")
    feed_configs = relationship("FeedConfig", back_populates="tenant", cascade="all, delete-orphan")
    scheduled_jobs = relationship("ScheduledJob", back_populates="tenant", cascade="all, delete-orphan")
    brand_configs = relationship("BrandConfig", back_populates="tenant", cascade="all, delete-orphan")
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    provider_credentials = relationship("ProviderCredential", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(slug='{self.slug}', name='{self.name}')>"


class ProviderCredential(Base):
    """Store encrypted provider credentials separately for security"""
    __tablename__ = 'provider_credentials'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)

    # Provider info
    provider = Column(String(50), nullable=False)  # openai, google, tiktok

    # Encrypted credentials (use application-level encryption)
    credentials_encrypted = Column(Text, nullable=False)

    # Metadata
    is_active = Column(Boolean, default=True, index=True)
    last_verified = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="provider_credentials")

    def __repr__(self):
        return f"<ProviderCredential(provider='{self.provider}', tenant_id='{self.tenant_id}')>"
