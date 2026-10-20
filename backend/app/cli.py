import typer

from app.core.exceptions import AppError
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.idempotency import IdempotencyService
from app.modules.auth.permissions import PermissionService
from app.modules.auth.repository import (
    AclRepository,
    TenantRepository,
    UserRepository,
)
from app.modules.auth.tenant_service import TenantService
from app.modules.auth.user_service import AdminUserService

app = typer.Typer(help="LexPilot 管理命令")


def _admin_service(db) -> AdminUserService:
    return AdminUserService(
        session=db,
        users=UserRepository(db),
        tenants=TenantRepository(db),
        permissions=PermissionService(AclRepository(db)),
        idempotency=IdempotencyService(db),
    )


@app.command("create-tenant")
def create_tenant(slug: str, name: str) -> None:
    with SessionLocal() as db:
        try:
            tenant = TenantService(db, TenantRepository(db)).create_tenant(slug, name)
        except AppError as exc:
            typer.echo(f"错误：{exc.message}")
            raise typer.Exit(code=1) from exc
        typer.echo(str(tenant.id))


@app.command("create-admin")
def create_admin(
    tenant_slug: str,
    email: str,
    password: str,
    display_name: str = "Administrator",
) -> None:
    with SessionLocal() as db:
        try:
            user = _admin_service(db).bootstrap_admin(
                tenant_slug=tenant_slug,
                email=email,
                password=password,
                display_name=display_name,
            )
        except AppError as exc:
            typer.echo(f"错误：{exc.message}")
            raise typer.Exit(code=1) from exc
        typer.echo(str(user.id))


@app.command("seed-dev")
def seed_dev() -> None:
    with SessionLocal() as db:
        try:
            tenant = TenantService(
                db,
                TenantRepository(db),
            ).get_or_create("acme", "Acme")
            user = _admin_service(db).bootstrap_admin(
                tenant_slug=tenant.slug,
                email="admin@example.com",
                password="Admin123!",
                display_name="Admin",
            )
        except AppError as exc:
            typer.echo(f"错误：{exc.message}")
            raise typer.Exit(code=1) from exc
        typer.echo(f"tenant={tenant.slug} email={user.email}")


if __name__ == "__main__":
    app()
