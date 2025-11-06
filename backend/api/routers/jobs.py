"""
Jobs Router
Handles CRUD operations for scheduled jobs/tasks
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api.database import get_db
from api import schemas
from api.auth import require_viewer, require_editor, require_admin
from models.user import User
from models.job import ScheduledJob, JobExecution
from datetime import datetime

router = APIRouter()


@router.get("/", response_model=List[schemas.ScheduledJob])
async def list_jobs(
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """
    List all scheduled jobs for the current user's tenant
    """
    jobs = db.query(ScheduledJob).filter(
        ScheduledJob.tenant_id == current_user.tenant_id
    ).order_by(ScheduledJob.created_at.desc()).all()

    return [schemas.ScheduledJob.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=schemas.ScheduledJob)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get a specific job by ID"""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Verify tenant access
    if job.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return schemas.ScheduledJob.model_validate(job)


@router.post("/", response_model=schemas.ScheduledJob, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: schemas.ScheduledJobCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Create a new scheduled job (requires editor role)

    - **job_type**: Type of job (monitor_feeds)
    - **schedule_cron**: Cron expression or "@manual" for manual-only
    - **enabled**: Whether the job is enabled
    - **config**: Job configuration including name, brand_ids, feed_ids
    """
    # Create job
    job = ScheduledJob(
        tenant_id=current_user.tenant_id,
        job_type=job_data.job_type,
        schedule_cron=job_data.schedule_cron,
        enabled=job_data.enabled,
        config=job_data.config or {}
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return schemas.ScheduledJob.model_validate(job)


@router.patch("/{job_id}", response_model=schemas.ScheduledJob)
@router.put("/{job_id}", response_model=schemas.ScheduledJob)
async def update_job(
    job_id: UUID,
    job_update: schemas.ScheduledJobUpdate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """Update a scheduled job (requires editor role)"""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Verify tenant access
    if job.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update fields
    update_data = job_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    return schemas.ScheduledJob.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a scheduled job (requires admin role)"""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Verify tenant access
    if job.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    db.delete(job)
    db.commit()
    return None


@router.post("/{job_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_job_now(
    job_id: UUID,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Manually trigger a job to run now (requires editor role)
    Returns 202 Accepted - job will be queued for execution
    """
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Verify tenant access
    if job.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Queue the job for execution via Celery
    from celery_app.tasks.scheduled_tasks import execute_scheduled_job

    # Trigger the Celery task asynchronously
    task = execute_scheduled_job.delay(str(job_id))

    return {
        "message": "Job queued for execution",
        "job_id": str(job_id),
        "task_id": task.id,
        "status": "queued"
    }


@router.get("/executions/", response_model=List[schemas.JobExecution])
async def list_all_executions(
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
    limit: int = 100
):
    """
    List all job executions for the current user's tenant
    Ordered by most recent first
    """
    executions = db.query(JobExecution).filter(
        JobExecution.tenant_id == current_user.tenant_id
    ).order_by(JobExecution.started_at.desc()).limit(limit).all()

    return [schemas.JobExecution.model_validate(execution) for execution in executions]


@router.get("/{job_id}/executions", response_model=List[schemas.JobExecution])
async def list_job_executions(
    job_id: UUID,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """
    List execution history for a specific job
    Ordered by most recent first
    """
    # First verify the job exists and user has access
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Verify tenant access
    if job.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    executions = db.query(JobExecution).filter(
        JobExecution.job_id == job_id
    ).order_by(JobExecution.started_at.desc()).limit(limit).all()

    return [schemas.JobExecution.model_validate(execution) for execution in executions]
