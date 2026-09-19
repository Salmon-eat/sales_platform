from app.main import app


def test_routes_are_versioned() -> None:
    paths = set(app.openapi()["paths"])
    assert {"/v1/health", "/v1/auth/google", "/v1/auth/me"} <= paths
    assert "/v1/auth/login" not in paths  # admin spec §1: no passwords
    assert all(path.startswith("/v1/") for path in paths)


async def test_admin_endpoints_require_a_session() -> None:
    """Every /v1/admin operation answers 401 without a session (admin spec §1: checks on the backend,
    not only hidden buttons). The check runs before any database access."""
    import re

    from httpx import ASGITransport, AsyncClient

    operations = [
        (method.upper(), re.sub(r"\{[^}]+\}", "1", path))
        for path, item in app.openapi()["paths"].items()
        if path.startswith("/v1/admin")
        for method in item
    ]
    assert len(operations) > 10
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for method, path in operations:
            response = await client.request(method, path)
            assert response.status_code == 401, (method, path, response.status_code)
            # a session cookie alone is not accepted: the token must come in the Authorization header
            response = await client.request(method, path, headers={"Cookie": "access_token=anything"})
            assert response.status_code == 401, (method, path)
