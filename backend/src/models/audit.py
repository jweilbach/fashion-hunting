"""
Audit Log model for security and compliance
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class AuditLog(Base):
    """Audit log for security and compliance tracking"""
    __tablename__ = 'audit_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), index=True)

    # Action details
    action = Column(String(100), nullable=False, index=True)  # login, create_report, update_feed
    resource_type = Column(String(100))  # tenant, report, feed
    resource_id = Column(UUID(as_uuid=True))

    # Context
    ip_address = Column(INET)
    user_agent = Column(Text)
    meta = Column('metadata', JSONB, default=dict)  # Renamed to avoid SQLAlchemy reserved word

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Constraints
    __table_args__ = (
        Index('idx_audit_logs_resource', 'resource_type', 'resource_id'),
    )

    def __repr__(self):
        return f"<AuditLog(action='{self.action}', resource='{self.resource_type}', created_at='{self.created_at}')>"

    def to_dict(self):
        """Convert audit log to dictionary"""
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id) if self.tenant_id else None,
            'user_id': str(self.user_id) if self.user_id else None,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': str(self.resource_id) if self.resource_id else None,
            'ip_address': str(self.ip_address) if self.ip_address else None,
            'user_agent': self.user_agent,
            'metadata': self.meta,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
