
"""
User model for multi-user access
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class User(Base):
    """User accounts with role-based access"""
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)

    # User info
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    full_name = Column(String(255))  # Kept for backwards compatibility

    # Permissions
    role = Column(String(50), default='viewer')  # admin, editor, viewer
    is_active = Column(Boolean, default=True, index=True)
    is_superuser = Column(Boolean, default=False, index=True)  # Cross-tenant super admin

    # Auth
    last_login = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    created_lists = relationship("List", back_populates="creator")
    added_list_items = relationship("ListItem", back_populates="adder")

    # Constraints
    __table_args__ = (
        Index('idx_users_tenant_email', 'tenant_id', 'email', unique=True),
        Index('idx_users_tenant_active', 'tenant_id', 'is_active'),
    )

    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role}', active={self.is_active})>"

    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary"""
        data = {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'is_superuser': self.is_superuser,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_sensitive:
            data['password_hash'] = self.password_hash

        return data
