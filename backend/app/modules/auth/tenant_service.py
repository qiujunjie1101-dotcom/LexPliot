from sqlalchemy.orm import Session

from app.core.exceptions import TenantAlreadyExists
from app.modules.auth.models import Tenant
from app.modules.auth.repository import TenantRepository


class TenantService:
    def __init__(self, session: Session, tenants: TenantRepository) -> None:
        self.session = session
        self.tenants = tenants

    def create_tenant(self, slug: str, name: str) -> Tenant:
        if self.tenants.get_by_slug(slug) is not None:
            raise TenantAlreadyExists()
        tenant = self.tenants.create(slug=slug, name=name)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return tenant

    def get_or_create(self, slug: str, name: str) -> Tenant:
        existing = self.tenants.get_by_slug(slug)
        if existing is not None:
            return existing
        tenant = self.tenants.create(slug=slug, name=name)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return tenant
