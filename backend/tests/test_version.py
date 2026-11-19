import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_get_version_defaults_to_dev(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/version")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"version": "dev"}


@pytest.mark.asyncio
async def test_get_version_uses_app_version(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/version")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"version": "1.2.3"}
