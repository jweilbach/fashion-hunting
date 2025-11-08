"""
Job and JobExecution repository for database operations
"""
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID

from models.job import ScheduledJob, JobExecution


class JobRepository:
    """Repository for ScheduledJob operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, job_id: UUID) -> Optional[ScheduledJob]:
        """Get scheduled job by ID"""
        return self.db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()

    def get_all(
        self,
        tenant_id: UUID,
        enabled_only: bool = False,
    ) -> List[ScheduledJob]:
        """Get all scheduled jobs for a tenant"""
        query = self.db.query(ScheduledJob).filter(ScheduledJob.tenant_id == tenant_id)

        if enabled_only:
            query = query.filter(ScheduledJob.enabled == True)

        return query.order_by(ScheduledJob.created_at.desc()).all()

    def get_enabled(self, tenant_id: UUID) -> List[ScheduledJob]:
        """Get all enabled jobs"""
        return self.get_all(tenant_id, enabled_only=True)

    def get_by_type(self, tenant_id: UUID, job_type: str) -> List[ScheduledJob]:
        """Get jobs by type"""
        return self.db.query(ScheduledJob).filter(
            ScheduledJob.tenant_id == tenant_id,
            ScheduledJob.job_type == job_type
        ).all()

    def create(self, **kwargs) -> ScheduledJob:
        """Create a new scheduled job"""
        job = ScheduledJob(**kwargs)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def update(self, job_id: UUID, **kwargs) -> Optional[ScheduledJob]:
        """Update a scheduled job"""
        job = self.get_by_id(job_id)
        if job:
            for key, value in kwargs.items():
                setattr(job, key, value)
            self.db.commit()
            self.db.refresh(job)
        return job

    def delete(self, job_id: UUID) -> bool:
        """Delete a scheduled job"""
        job = self.get_by_id(job_id)
        if job:
            self.db.delete(job)
            self.db.commit()
            return True
        return False

    def enable(self, job_id: UUID) -> Optional[ScheduledJob]:
        """Enable a job"""
        return self.update(job_id, enabled=True)

    def disable(self, job_id: UUID) -> Optional[ScheduledJob]:
        """Disable a job"""
        return self.update(job_id, enabled=False)

    def update_last_run(
        self,
        job_id: UUID,
        status: str,
        error: Optional[str] = None,
        next_run: Optional[datetime] = None
    ) -> Optional[ScheduledJob]:
        """Update last run information"""
        job = self.get_by_id(job_id)
        if job:
            job.last_run = datetime.now(timezone.utc)
            job.last_status = status
            job.last_error = error
            job.run_count += 1
            if next_run:
                job.next_run = next_run
            self.db.commit()
            self.db.refresh(job)
        return job

    def count(self, tenant_id: UUID, enabled_only: bool = False) -> int:
        """Count jobs for a tenant"""
        query = self.db.query(func.count(ScheduledJob.id)).filter(
            ScheduledJob.tenant_id == tenant_id
        )
        if enabled_only:
            query = query.filter(ScheduledJob.enabled == True)
        return query.scalar() or 0


class JobExecutionRepository:
    """Repository for JobExecution operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, execution_id: UUID) -> Optional[JobExecution]:
        """Get job execution by ID"""
        return self.db.query(JobExecution).filter(JobExecution.id == execution_id).first()

    def get_all(
        self,
        tenant_id: UUID,
        job_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[JobExecution]:
        """Get job executions for a tenant"""
        query = self.db.query(JobExecution).filter(JobExecution.tenant_id == tenant_id)

        if job_id:
            query = query.filter(JobExecution.job_id == job_id)

        return query.order_by(JobExecution.started_at.desc()).limit(limit).all()

    def get_by_job(self, job_id: UUID, limit: int = 50) -> List[JobExecution]:
        """Get executions for a specific job"""
        return self.db.query(JobExecution).filter(
            JobExecution.job_id == job_id
        ).order_by(JobExecution.started_at.desc()).limit(limit).all()

    def get_recent(self, tenant_id: UUID, limit: int = 10) -> List[JobExecution]:
        """Get recent executions for a tenant"""
        return self.get_all(tenant_id, limit=limit)

    def get_latest_for_job(self, job_id: UUID) -> Optional[JobExecution]:
        """Get the most recent execution for a job"""
        return self.db.query(JobExecution).filter(
            JobExecution.job_id == job_id
        ).order_by(JobExecution.started_at.desc()).first()

    def create(self, **kwargs) -> JobExecution:
        """Create a new job execution record"""
        execution = JobExecution(**kwargs)
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def update(self, execution_id: UUID, **kwargs) -> Optional[JobExecution]:
        """Update a job execution"""
        execution = self.get_by_id(execution_id)
        if execution:
            for key, value in kwargs.items():
                setattr(execution, key, value)
            self.db.commit()
            self.db.refresh(execution)
        return execution

    def complete(
        self,
        execution_id: UUID,
        status: str,
        items_processed: int = 0,
        items_failed: int = 0,
        error_message: Optional[str] = None,
        execution_log: Optional[str] = None
    ) -> Optional[JobExecution]:
        """Mark an execution as completed"""
        return self.update(
            execution_id,
            completed_at=datetime.now(timezone.utc),
            status=status,
            items_processed=items_processed,
            items_failed=items_failed,
            error_message=error_message,
            execution_log=execution_log
        )

    def count(self, tenant_id: UUID, job_id: Optional[UUID] = None) -> int:
        """Count executions"""
        query = self.db.query(func.count(JobExecution.id)).filter(
            JobExecution.tenant_id == tenant_id
        )
        if job_id:
            query = query.filter(JobExecution.job_id == job_id)
        return query.scalar() or 0
