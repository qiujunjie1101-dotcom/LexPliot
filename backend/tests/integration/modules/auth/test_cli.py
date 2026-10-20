from typer.testing import CliRunner

from app.cli import app as cli_app


def test_seed_dev_creates_loginable_admin(client) -> None:
    result = CliRunner().invoke(cli_app, ["seed-dev"])
    assert result.exit_code == 0, result.output
    assert "tenant=acme" in result.output

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": "Admin123!",
            "tenant_slug": "acme",
        },
    )
    assert response.status_code == 200
    assert response.json()["roles"] == ["admin"]


def test_create_tenant_and_admin_for_new_tenant(client) -> None:
    runner = CliRunner()
    tenant_result = runner.invoke(cli_app, ["create-tenant", "beta", "Beta"])
    assert tenant_result.exit_code == 0, tenant_result.output

    admin_result = runner.invoke(
        cli_app,
        [
            "create-admin",
            "beta",
            "beta-admin@example.com",
            "BetaAdmin123!",
            "--display-name",
            "Beta Admin",
        ],
    )
    assert admin_result.exit_code == 0, admin_result.output

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "beta-admin@example.com",
            "password": "BetaAdmin123!",
            "tenant_slug": "beta",
        },
    )
    assert response.status_code == 200
    assert response.json()["tenant"]["slug"] == "beta"
    assert response.json()["roles"] == ["admin"]
