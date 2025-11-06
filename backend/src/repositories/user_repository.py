"""
User repository for database operations
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from uuid import UUID

from models.user import User


class UserRepository:
    """Repository for User operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str, tenant_id: Optional[UUID] = None) -> Optional[User]:
        """Get user by email (optionally scoped to tenant)"""
        query = self.db.query(User).filter(User.email == email)

        if tenant_id:
            query = query.filter(User.tenant_id == tenant_id)

        return query.first()

    def get_all(
        self,
        tenant_id: UUID,
        active_only: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get all users for a tenant"""
        query = self.db.query(User).filter(User.tenant_id == tenant_id)

        if active_only:
            query = query.filter(User.is_active == True)

        return query.offset(skip).limit(limit).all()

    def create(self, **kwargs) -> User:
        """Create a new user"""
        user = User(**kwargs)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user_id: UUID, **kwargs) -> Optional[User]:
        """Update a user"""
        user = self.get_by_id(user_id)
        if user:
            for key, value in kwargs.items():
                setattr(user, key, value)
            self.db.commit()
            self.db.refresh(user)
        return user

    def delete(self, user_id: UUID) -> bool:
        """Delete a user"""
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False

    def update_last_login(self, user_id: UUID) -> Optional[User]:
        """Update user's last login timestamp"""
        user = self.get_by_id(user_id)
        if user:
            user.last_login = datetime.now()
            self.db.commit()
            self.db.refresh(user)
        return user

    def activate(self, user_id: UUID) -> Optional[User]:
        """Activate a user"""
        return self.update(user_id, is_active=True)

    def deactivate(self, user_id: UUID) -> Optional[User]:
        """Deactivate a user"""
        return self.update(user_id, is_active=False)

    def change_password(self, user_id: UUID, password_hash: str) -> Optional[User]:
        """Change user password"""
        return self.update(user_id, password_hash=password_hash)

    def count(self, tenant_id: UUID, active_only: bool = False) -> int:
        """Count users for a tenant"""
        query = self.db.query(User).filter(User.tenant_id == tenant_id)

        if active_only:
            query = query.filter(User.is_active == True)

        return query.count()
