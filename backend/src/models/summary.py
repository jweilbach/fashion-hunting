"""
Summary model for AI-generated PDF summary documents
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class Summary(Base):
    """AI-generated PDF summary document"""
    __tablename__ = 'summaries'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey('scheduled_jobs.id', ondelete='SET NULL'), nullable=True, index=True)
    execution_id = Column(UUID(as_uuid=True), ForeignKey('job_executions.id', ondelete='SET NULL'), nullable=True, index=True)

    # Brands included in summary
    brand_ids = Column(ARRAY(UUID(as_uuid=True)), default=list)

    # Summary content
    title = Column(String(500), nullable=False)
    executive_summary = Column(Text)

    # Time range covered
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))

    # File storage (Phase 1 - local filesystem)
    file_path = Column(String(500))
    file_size_bytes = Column(Integer)

    # Statistics
    report_count = Column(Integer, default=0)

    # Generation status
    generation_status = Column(String(50), default='pending', index=True)  # pending, generating, completed, failed
    generation_error = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", backref="summaries")
    job = relationship("ScheduledJob", backref="summaries")
    execution = relationship("JobExecution", backref="summaries")

    def __repr__(self):
        return f"<Summary(title='{self.title}', status='{self.generation_status}', reports={self.report_count})>"

    def to_dict(self):
        """Convert summary to dictionary"""
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'job_id': str(self.job_id) if self.job_id else None,
            'execution_id': str(self.execution_id) if self.execution_id else None,
            'brand_ids': [str(bid) for bid in (self.brand_ids or [])],
            'title': self.title,
            'executive_summary': self.executive_summary,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'file_path': self.file_path,
            'file_size_bytes': self.file_size_bytes,
            'report_count': self.report_count,
            'generation_status': self.generation_status,
            'generation_error': self.generation_error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
