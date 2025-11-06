"""
Tenant repository for database operations
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from uuid import UUID

from models.tenant import Tenant, ProviderCredential


class TenantRepository:
    """Repository for Tenant operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID"""
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug"""
        return self.db.query(Tenant).filter(Tenant.slug == slug).first()

    def get_by_email(self, email: str) -> Optional[Tenant]:
        """Get tenant by email"""
        return self.db.query(Tenant).filter(Tenant.email == email).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        """Get all tenants with pagination"""
        return self.db.query(Tenant).offset(skip).limit(limit).all()

    def get_active(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        """Get all active tenants"""
        return (
            self.db.query(Tenant)
            .filter(Tenant.status == 'active')
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, **kwargs) -> Tenant:
        """Create a new tenant"""
        tenant = Tenant(**kwargs)
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def update(self, tenant_id: UUID, **kwargs) -> Optional[Tenant]:
        """Update a tenant"""
        tenant = self.get_by_id(tenant_id)
        if tenant:
            for key, value in kwargs.items():
                setattr(tenant, key, value)
            self.db.commit()
            self.db.refresh(tenant)
        return tenant

    def delete(self, tenant_id: UUID) -> bool:
        """Delete a tenant"""
        tenant = self.get_by_id(tenant_id)
        if tenant:
            self.db.delete(tenant)
            self.db.commit()
            return True
        return False

    # Provider Credentials methods

    def get_provider_credential(
        self, tenant_id: UUID, provider: str
    ) -> Optional[ProviderCredential]:
        """Get provider credential for tenant"""
        return (
            self.db.query(ProviderCredential)
            .filter(
                ProviderCredential.tenant_id == tenant_id,
                ProviderCredential.provider == provider,
                ProviderCredential.is_active == True
            )
            .first()
        )

    def set_provider_credential(
        self, tenant_id: UUID, provider: str, credentials_encrypted: str
    ) -> ProviderCredential:
        """Set or update provider credential"""
        cred = self.get_provider_credential(tenant_id, provider)

        if cred:
            cred.credentials_encrypted = credentials_encrypted
        else:
            cred = ProviderCredential(
                tenant_id=tenant_id,
                provider=provider,
                credentials_encrypted=credentials_encrypted
            )
            self.db.add(cred)

        self.db.commit()
        self.db.refresh(cred)
        return cred
