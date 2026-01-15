"""
Admin Router
Handles super admin operations for cross-tenant management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
import sys
from pathlib import Path
import math
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api.database import get_db
from api import schemas
from api.auth import require_superadmin, create_impersonation_token
from api.config import settings
from models.user import User
from models.tenant import Tenant
from models.report import Report
from repositories.tenant_repository import TenantRepository
from repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tenants", response_model=schemas.TenantListResponse)
async def list_tenants(
    status_filter: Optional[str] = Query(None, description="Filter by status (active, suspended, cancelled)"),
    plan_filter: Optional[str] = Query(None, description="Filter by plan (free, starter, professional, enterprise)"),
    search: Optional[str] = Query(None, description="Search by name, slug, or email"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    List all tenants with their stats (superuser only)

    Returns paginated list of tenants with user count and report count.
    """
    query = db.query(Tenant)

    # Apply filters
    if status_filter:
        query = query.filter(Tenant.status == status_filter)
    if plan_filter:
        query = query.filter(Tenant.plan == plan_filter)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Tenant.name.ilike(search_term)) |
            (Tenant.slug.ilike(search_term)) |
            (Tenant.email.ilike(search_term))
        )

    # Get total count
    total = query.count()

    # Apply pagination
    skip = (page - 1) * page_size
    tenants = query.order_by(Tenant.created_at.desc()).offset(skip).limit(page_size).all()

    # Build response with counts
    items = []
    for tenant in tenants:
        user_count = db.query(func.count(User.id)).filter(User.tenant_id == tenant.id).scalar()
        report_count = db.query(func.count(Report.id)).filter(Report.tenant_id == tenant.id).scalar()

        items.append(schemas.TenantAdminResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            email=tenant.email,
            company_name=tenant.company_name,
            plan=tenant.plan,
            status=tenant.status,
            user_count=user_count or 0,
            report_count=report_count or 0,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            last_report_run=tenant.last_report_run
        ))

    return schemas.TenantListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/tenants/{tenant_id}", response_model=schemas.TenantAdminResponse)
async def get_tenant(
    tenant_id: UUID,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get detailed tenant information (superuser only)
    """
    repo = TenantRepository(db)
    tenant = repo.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    user_count = db.query(func.count(User.id)).filter(User.tenant_id == tenant.id).scalar()
    report_count = db.query(func.count(Report.id)).filter(Report.tenant_id == tenant.id).scalar()

    return schemas.TenantAdminResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        email=tenant.email,
        company_name=tenant.company_name,
        plan=tenant.plan,
        status=tenant.status,
        user_count=user_count or 0,
        report_count=report_count or 0,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        last_report_run=tenant.last_report_run
    )


@router.patch("/tenants/{tenant_id}/status", response_model=schemas.TenantAdminResponse)
async def update_tenant_status(
    tenant_id: UUID,
    status_update: schemas.TenantStatusUpdate,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Update tenant status (suspend/activate/cancel) (superuser only)

    - **status**: active, suspended, or cancelled
    """
    repo = TenantRepository(db)
    tenant = repo.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    updated_tenant = repo.update(tenant_id, status=status_update.status)

    user_count = db.query(func.count(User.id)).filter(User.tenant_id == tenant.id).scalar()
    report_count = db.query(func.count(Report.id)).filter(Report.tenant_id == tenant.id).scalar()

    return schemas.TenantAdminResponse(
        id=updated_tenant.id,
        name=updated_tenant.name,
        slug=updated_tenant.slug,
        email=updated_tenant.email,
        company_name=updated_tenant.company_name,
        plan=updated_tenant.plan,
        status=updated_tenant.status,
        user_count=user_count or 0,
        report_count=report_count or 0,
        created_at=updated_tenant.created_at,
        updated_at=updated_tenant.updated_at,
        last_report_run=updated_tenant.last_report_run
    )


@router.patch("/tenants/{tenant_id}/plan", response_model=schemas.TenantAdminResponse)
async def update_tenant_plan(
    tenant_id: UUID,
    plan_update: schemas.TenantPlanUpdate,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Update tenant subscription plan (superuser only)

    - **plan**: free, starter, professional, or enterprise
    """
    repo = TenantRepository(db)
    tenant = repo.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    updated_tenant = repo.update(tenant_id, plan=plan_update.plan)

    user_count = db.query(func.count(User.id)).filter(User.tenant_id == tenant.id).scalar()
    report_count = db.query(func.count(Report.id)).filter(Report.tenant_id == tenant.id).scalar()

    return schemas.TenantAdminResponse(
        id=updated_tenant.id,
        name=updated_tenant.name,
        slug=updated_tenant.slug,
        email=updated_tenant.email,
        company_name=updated_tenant.company_name,
        plan=updated_tenant.plan,
        status=updated_tenant.status,
        user_count=user_count or 0,
        report_count=report_count or 0,
        created_at=updated_tenant.created_at,
        updated_at=updated_tenant.updated_at,
        last_report_run=updated_tenant.last_report_run
    )


@router.post("/impersonate/{user_id}", response_model=schemas.ImpersonationResponse)
async def impersonate_user(
    user_id: UUID,
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get an impersonation token to act as another user (superuser only)

    This creates a special token that allows the super admin to access
    the system as the target user. The token includes tracking info
    that identifies this as an impersonation session.

    Security notes:
    - Cannot impersonate other superusers
    - Token expires in 1 hour
    - All actions are logged with 'impersonated_by: super_admin:email'
    """
    user_repo = UserRepository(db)
    target_user = user_repo.get_by_id(user_id)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Security: Cannot impersonate other superusers
    if target_user.is_superuser:
        logger.warning(f"Impersonation blocked: super admin '{current_user.email}' attempted to impersonate another super admin '{target_user.email}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot impersonate another super admin"
        )

    # Create impersonation token
    token = create_impersonation_token(target_user, current_user.email)

    # Log the impersonation
    logger.info(f"IMPERSONATION STARTED: super admin '{current_user.email}' is now impersonating user '{target_user.email}' (tenant: {target_user.tenant_id})")

    return schemas.ImpersonationResponse(
        access_token=token,
        token_type="bearer",
        expires_in=3600,  # 1 hour
        impersonated_user=schemas.User.model_validate(target_user),
        impersonated_by=f"super_admin:{current_user.email}"
    )


@router.get("/search/users", response_model=List[schemas.AdminUserSearchResult])
async def search_users(
    query: str = Query(..., min_length=2, description="Search query (email, name)"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Search for users across all tenants (superuser only)

    Searches by email, first name, last name, or full name.
    Returns users with their tenant information.
    """
    search_term = f"%{query}%"

    users = (
        db.query(User, Tenant.name.label("tenant_name"))
        .join(Tenant, User.tenant_id == Tenant.id)
        .filter(
            (User.email.ilike(search_term)) |
            (User.first_name.ilike(search_term)) |
            (User.last_name.ilike(search_term)) |
            (User.full_name.ilike(search_term))
        )
        .order_by(User.email)
        .limit(limit)
        .all()
    )

    results = []
    for user, tenant_name in users:
        results.append(schemas.AdminUserSearchResult(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            tenant_id=user.tenant_id,
            tenant_name=tenant_name,
            created_at=user.created_at
        ))

    return results


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get high-level system statistics (superuser only)
    """
    total_tenants = db.query(func.count(Tenant.id)).scalar()
    active_tenants = db.query(func.count(Tenant.id)).filter(Tenant.status == 'active').scalar()
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    total_reports = db.query(func.count(Report.id)).scalar()

    # Plan breakdown
    plan_counts = (
        db.query(Tenant.plan, func.count(Tenant.id))
        .group_by(Tenant.plan)
        .all()
    )
    plans = {plan: count for plan, count in plan_counts}

    return {
        "tenants": {
            "total": total_tenants or 0,
            "active": active_tenants or 0,
        },
        "users": {
            "total": total_users or 0,
            "active": active_users or 0,
        },
        "reports": {
            "total": total_reports or 0,
        },
        "plans": plans,
    }
