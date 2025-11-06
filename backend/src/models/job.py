"""
Scheduled Job and Job Execution models
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class ScheduledJob(Base):
    """Scheduled job configuration"""
    __tablename__ = 'scheduled_jobs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)

    # Job configuration
    job_type = Column(String(50), nullable=False)  # fetch_reports, send_digest, generate_slides
    schedule_cron = Column(String(100), nullable=False)  # Cron expression
    enabled = Column(Boolean, default=True, index=True)

    # Job settings
    config = Column(JSONB, default=dict)

    # Execution tracking
    last_run = Column(DateTime(timezone=True))
    last_status = Column(String(50))  # success, failed, running
    last_error = Column(Text)
    next_run = Column(DateTime(timezone=True), index=True)
    run_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="scheduled_jobs")
    executions = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ScheduledJob(job_type='{self.job_type}', schedule='{self.schedule_cron}', enabled={self.enabled})>"

    def to_dict(self):
        """Convert job to dictionary"""
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'job_type': self.job_type,
            'schedule_cron': self.schedule_cron,
            'enabled': self.enabled,
            'config': self.config,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'last_status': self.last_status,
            'last_error': self.last_error,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'run_count': self.run_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class JobExecution(Base):
    """Job execution history"""
    __tablename__ = 'job_executions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey('scheduled_jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)

    # Execution details
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True))
    status = Column(String(50), nullable=False, index=True)  # running, success, failed, partial

    # Results
    items_processed = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    error_message = Column(Text)
    execution_log = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    job = relationship("ScheduledJob", back_populates="executions")

    def __repr__(self):
        return f"<JobExecution(job_id='{self.job_id}', status='{self.status}', started_at='{self.started_at}')>"

    def to_dict(self):
        """Convert execution to dictionary"""
        return {
            'id': str(self.id),
            'job_id': str(self.job_id),
            'tenant_id': str(self.tenant_id),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'items_processed': self.items_processed,
            'items_failed': self.items_failed,
            'error_message': self.error_message,
            'execution_log': self.execution_log,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
