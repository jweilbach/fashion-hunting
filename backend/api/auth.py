"""
Authentication and authorization utilities
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID

from api.config import settings
from api.database import get_db
from api.schemas import TokenData
from models.user import User

logger = logging.getLogger(__name__)


# HTTP Bearer token scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """Decode and validate a JWT access token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        email: str = payload.get("email")
        role: str = payload.get("role")

        if user_id is None:
            raise credentials_exception

        token_data = TokenData(
            user_id=UUID(user_id) if user_id else None,
            tenant_id=UUID(tenant_id) if tenant_id else None,
            email=email,
            role=role
        )

        return token_data

    except JWTError:
        raise credentials_exception


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password"""
    user = db.query(User).filter(User.email == email).first()

    if not user:
        logger.warning(f"Login failed: user not found for email '{email}'")
        return None

    if not verify_password(password, user.password_hash):
        logger.warning(f"Login failed: invalid password for email '{email}'")
        return None

    if not user.is_active:
        logger.warning(f"Login failed: inactive user '{email}'")
        return None

    logger.info(f"Login successful for user '{email}'")
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token

    Usage:
        @app.get("/me")
        def read_current_user(current_user: User = Depends(get_current_user)):
            return current_user
    """
    token = credentials.credentials
    token_data = decode_access_token(token)

    user = db.query(User).filter(User.id == token_data.user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (alias for get_current_user)"""
    return current_user


class RoleChecker:
    """
    Dependency to check if user has required role

    Usage:
        require_admin = RoleChecker(["admin"])

        @app.delete("/users/{user_id}")
        def delete_user(
            user_id: UUID,
            current_user: User = Depends(require_admin)
        ):
            ...
    """

    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of: {', '.join(self.allowed_roles)}"
            )
        return user


# Pre-configured role checkers
require_admin = RoleChecker(["admin"])
require_editor = RoleChecker(["admin", "editor"])
require_viewer = RoleChecker(["admin", "editor", "viewer"])


class SuperAdminChecker:
    """
    Dependency to check if user is a superuser (cross-tenant admin)

    Usage:
        require_superadmin = SuperAdminChecker()

        @app.get("/admin/tenants")
        def list_tenants(
            current_user: User = Depends(require_superadmin)
        ):
            ...
    """

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super admin access required"
            )
        return user


# Pre-configured super admin checker
require_superadmin = SuperAdminChecker()


def create_impersonation_token(
    target_user: User,
    superadmin_email: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create an impersonation token for a super admin to act as another user.

    The token includes 'impersonated_by' field to track the super admin's email
    for audit logging purposes.

    Args:
        target_user: The user to impersonate
        superadmin_email: Email of the super admin performing impersonation
        expires_delta: Optional expiry time (defaults to 1 hour for safety)

    Returns:
        JWT token for the impersonated session
    """
    # Default to 1 hour for impersonation tokens (shorter for security)
    if expires_delta is None:
        expires_delta = timedelta(hours=1)

    data = {
        "sub": str(target_user.id),
        "tenant_id": str(target_user.tenant_id),
        "email": target_user.email,
        "role": target_user.role,
        "impersonated_by": f"super_admin:{superadmin_email}",
    }

    return create_access_token(data, expires_delta)


def get_impersonation_info(token: str) -> Optional[str]:
    """
    Extract impersonation info from a token if present.

    Returns:
        The 'impersonated_by' value if this is an impersonation token, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("impersonated_by")
    except JWTError:
        return None
