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
from repositories.job_repository import JobRepository, JobExecutionRepository
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
    job_repo = JobRepository(db)
    jobs = job_repo.get_all(current_user.tenant_id)

    return [schemas.ScheduledJob.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=schemas.ScheduledJob)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    """Get a specific job by ID"""
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)

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
    job_repo = JobRepository(db)
    job = job_repo.create(
        tenant_id=current_user.tenant_id,
        job_type=job_data.job_type,
        schedule_cron=job_data.schedule_cron,
        enabled=job_data.enabled,
        config=job_data.config or {}
    )

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
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)

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
    job = job_repo.update(job_id, **update_data)

    return schemas.ScheduledJob.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a scheduled job (requires admin role)"""
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)

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

    job_repo.delete(job_id)
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

    Prevents duplicate runs by checking if job is already running
    """
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)

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

    # Check if job is already running
    if job.last_status == 'running':
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is already running. Please wait for the current execution to complete."
        )

    # Check for any running executions of this job
    execution_repo = JobExecutionRepository(db)
    running_executions = db.query(JobExecution).filter(
        JobExecution.job_id == job_id,
        JobExecution.status == 'running'
    ).first()

    if running_executions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is already running. Please wait for the current execution to complete."
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
    execution_repo = JobExecutionRepository(db)
    executions = execution_repo.get_all(current_user.tenant_id, limit=limit)

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
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)

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

    execution_repo = JobExecutionRepository(db)
    executions = execution_repo.get_by_job_id(job_id, limit=limit)

    return [schemas.JobExecution.model_validate(execution) for execution in executions]
