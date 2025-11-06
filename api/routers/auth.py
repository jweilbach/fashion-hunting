"""
Authentication Router
Handles user login, registration, and token management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api.database import get_db
from api.config import settings
from api import schemas
from api.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_current_user,
    get_current_active_user
)
from models.user import User
from models.tenant import Tenant
from repositories.user_repository import UserRepository
from repositories.tenant_repository import TenantRepository

router = APIRouter()


@router.post("/login", response_model=schemas.LoginResponse)
async def login(
    login_data: schemas.LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login endpoint - authenticate user and return JWT token

    Args:
        login_data: Email and password
        db: Database session

    Returns:
        Access token and user information

    Raises:
        401: Invalid credentials
    """
    # Authenticate user
    user = authenticate_user(db, login_data.email, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "email": user.email,
            "role": user.role
        },
        expires_delta=access_token_expires
    )

    # Update last login
    user_repo = UserRepository(db)
    user_repo.update_last_login(user.id)

    # Return token and user info
    return schemas.LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        user=schemas.User.model_validate(user)
    )


@router.post("/token")
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token endpoint

    Args:
        form_data: OAuth2 username (email) and password
        db: Database session

    Returns:
        Access token

    Raises:
        401: Invalid credentials
    """
    # Authenticate user using email as username
    user = authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "email": user.email,
            "role": user.role
        },
        expires_delta=access_token_expires
    )

    # Update last login
    user_repo = UserRepository(db)
    user_repo.update_last_login(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/signup")
async def signup(
    signup_data: dict,
    db: Session = Depends(get_db)
):
    """
    Sign up a new user and create a new tenant

    Args:
        signup_data: User signup data (email, password, tenant_name)
        db: Database session

    Returns:
        Access token

    Raises:
        400: User already exists
    """
    try:
        email = signup_data.get("email")
        password = signup_data.get("password")
        tenant_name = signup_data.get("tenant_name")

        if not email or not password or not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email, password, and tenant_name are required"
            )

        user_repo = UserRepository(db)
        tenant_repo = TenantRepository(db)

        # Check if user already exists (across all tenants)
        existing_users = db.query(User).filter(User.email == email).all()
        if existing_users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        # Create new tenant with user's email
        tenant = tenant_repo.create(
            name=tenant_name,
            slug=tenant_name.lower().replace(" ", "-"),
            email=email,  # Use user's email for tenant contact
            company_name=tenant_name
        )

        # Hash password
        hashed_password = get_password_hash(password)

        # Create user as admin of the new tenant
        user = user_repo.create(
            tenant_id=tenant.id,
            email=email,
            password_hash=hashed_password,
            full_name=email.split("@")[0],  # Use email prefix as name
            role="admin"
        )

        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "tenant_id": str(user.tenant_id),
                "email": user.email,
                "role": user.role
            },
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create account: {str(e)}"
        )


@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        Created user information

    Raises:
        400: User already exists
    """
    user_repo = UserRepository(db)

    # Check if user already exists
    existing_user = user_repo.get_by_email(user_data.email, user_data.tenant_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists for this tenant"
        )

    # Hash password
    hashed_password = get_password_hash(user_data.password)

    # Create user
    user = user_repo.create(
        tenant_id=user_data.tenant_id,
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role
    )

    return schemas.User.model_validate(user)


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information

    Args:
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Current user information with tenant name
    """
    # Get tenant information
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "tenant_id": str(current_user.tenant_id),
        "tenant_name": tenant.name if tenant else None,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }


@router.post("/change-password")
async def change_password(
    password_data: schemas.UserChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password

    Args:
        password_data: Current and new password
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        400: Invalid current password
    """
    from api.auth import verify_password

    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Hash new password
    new_password_hash = get_password_hash(password_data.new_password)

    # Update password
    user_repo = UserRepository(db)
    user_repo.change_password(current_user.id, new_password_hash)

    return {"message": "Password changed successfully"}


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout endpoint (client should discard token)

    Note: JWT tokens are stateless, so we can't invalidate them server-side.
    The client should discard the token on logout.

    Args:
        current_user: Authenticated user

    Returns:
        Success message
    """
    return {"message": "Logged out successfully"}
