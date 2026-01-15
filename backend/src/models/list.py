"""
List and ListItem models for organizing reports and other objects
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class List(Base):
    """List for organizing reports and other objects"""
    __tablename__ = 'lists'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)

    # List metadata
    name = Column(String(255), nullable=False)
    list_type = Column(String(50), nullable=False)  # report, contact, editor, etc.
    description = Column(Text)

    # Ownership
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="lists")
    creator = relationship("User", back_populates="created_lists")
    items = relationship("ListItem", back_populates="list", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_lists_tenant_type', 'tenant_id', 'list_type'),
    )

    def __repr__(self):
        return f"<List(name='{self.name}', type='{self.list_type}', items={len(self.items) if self.items else 0})>"

    def to_dict(self, include_items=False):
        """Convert list to dictionary"""
        result = {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'name': self.name,
            'list_type': self.list_type,
            'description': self.description,
            'created_by': str(self.created_by) if self.created_by else None,
            'creator_name': self.creator.full_name if self.creator else None,
            'item_count': len(self.items) if self.items else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_items and self.items:
            result['items'] = [item.to_dict() for item in self.items]
        return result


class ListItem(Base):
    """Item within a list"""
    __tablename__ = 'list_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    list_id = Column(UUID(as_uuid=True), ForeignKey('lists.id', ondelete='CASCADE'), nullable=False, index=True)

    # Generic item reference
    item_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Tracking
    added_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))

    # Timestamps
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    list = relationship("List", back_populates="items")
    adder = relationship("User", back_populates="added_list_items")

    # Constraints
    __table_args__ = (
        Index('idx_list_items_unique', 'list_id', 'item_id', unique=True),
    )

    def __repr__(self):
        return f"<ListItem(list_id='{self.list_id}', item_id='{self.item_id}')>"

    def to_dict(self):
        """Convert list item to dictionary"""
        return {
            'id': str(self.id),
            'list_id': str(self.list_id),
            'item_id': str(self.item_id),
            'added_by': str(self.added_by) if self.added_by else None,
            'adder_name': self.adder.full_name if self.adder else None,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
