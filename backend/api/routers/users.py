"""
Users Router
Handles user management operations for tenant admins
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api.database import get_db
from api import schemas
from api.auth import get_current_user, require_admin, get_password_hash
from models.user import User
from repositories.user_repository import UserRepository

router = APIRouter()

# Default password for new users created by admin
DEFAULT_PASSWORD = "Welcome123"


@router.get("/", response_model=List[schemas.UserResponse])
async def list_users(
    active_only: Optional[bool] = Query(False, description="Filter active users only"),
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max users to return"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List all users for the current user's tenant (admin only)

    - **active_only**: Filter to show only active users (optional)
    - **skip**: Pagination offset
    - **limit**: Maximum number of users to return
    """
    repo = UserRepository(db)
    users = repo.get_all(
        tenant_id=current_user.tenant_id,
        active_only=active_only,
        skip=skip,
        limit=limit
    )
    return [schemas.UserResponse.model_validate(u) for u in users]


@router.get("/count")
async def get_user_count(
    active_only: Optional[bool] = Query(False, description="Count only active users"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get the total count of users for the tenant (admin only)"""
    repo = UserRepository(db)
    count = repo.count(current_user.tenant_id, active_only=active_only)
    return {"count": count}


@router.get("/{user_id}", response_model=schemas.UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get a specific user by ID (admin only)"""
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify tenant access
    if user.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return schemas.UserResponse.model_validate(user)


@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: schemas.UserCreateByAdmin,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user in the tenant (admin only)

    Creates a user with the default password "Welcome123".
    The user should change this password upon first login.

    - **email**: User's email address (must be unique within tenant)
    - **first_name**: User's first name (optional)
    - **last_name**: User's last name (optional)
    - **role**: User role - admin, editor, or viewer (default: viewer)
    """
    repo = UserRepository(db)

    # Check if user with this email already exists in the tenant
    existing_user = repo.get_by_email(user_data.email, tenant_id=current_user.tenant_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{user_data.email}' already exists in this organization"
        )

    # Create user with default password
    password_hash = get_password_hash(DEFAULT_PASSWORD)

    # Build full_name from first_name and last_name
    full_name = None
    if user_data.first_name or user_data.last_name:
        full_name = " ".join(filter(None, [user_data.first_name, user_data.last_name]))

    user = repo.create(
        tenant_id=current_user.tenant_id,
        email=user_data.email,
        password_hash=password_hash,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        full_name=full_name,
        role=user_data.role,
        is_active=True
    )

    return schemas.UserResponse.model_validate(user)


@router.patch("/{user_id}/role", response_model=schemas.UserResponse)
async def update_user_role(
    user_id: UUID,
    role_update: schemas.UserRoleUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Change a user's role (admin only)

    - **role**: New role - admin, editor, or viewer

    Note: Cannot change your own role (self-protection)
    """
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify tenant access
    if user.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Prevent changing own role
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )

    updated_user = repo.update(user_id, role=role_update.role)
    return schemas.UserResponse.model_validate(updated_user)


@router.patch("/{user_id}/activate", response_model=schemas.UserResponse)
async def activate_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Activate a user (admin only)

    Reactivates a previously deactivated user account.
    """
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify tenant access
    if user.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already active"
        )

    updated_user = repo.activate(user_id)
    return schemas.UserResponse.model_validate(updated_user)


@router.patch("/{user_id}/deactivate", response_model=schemas.UserResponse)
async def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Deactivate a user (admin only)

    Deactivates a user account, preventing them from logging in.
    The account is not deleted and can be reactivated later.

    Note: Cannot deactivate yourself (self-protection)
    """
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify tenant access
    if user.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Prevent deactivating self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already deactivated"
        )

    updated_user = repo.deactivate(user_id)
    return schemas.UserResponse.model_validate(updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a user (admin only)

    Permanently deletes a user account. This action cannot be undone.
    Consider deactivating the user instead if you may need the account later.

    Note: Cannot delete yourself (self-protection)
    """
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify tenant access
    if user.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Prevent deleting self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    repo.delete(user_id)
    return None
