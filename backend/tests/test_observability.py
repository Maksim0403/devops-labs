import json

import pytest
from fastapi import status
from httpx import AsyncClient

from app.main import access_log


@pytest.mark.asyncio
async def test_fail_endpoint_emits_structured_access_log(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages = []
    monkeypatch.setattr(access_log, "info", messages.append)
    monkeypatch.setenv("APP_VERSION", "test-version")

    response = await client.get("/fail")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    log_entry = json.loads(messages[0])
    assert set(log_entry) == {
        "level",
        "msg",
        "method",
        "route",
        "status",
        "duration_ms",
        "version",
    }
    assert log_entry["level"] == "error"
    assert log_entry["msg"] == "request"
    assert log_entry["method"] == "GET"
    assert log_entry["route"] == "/fail"
    assert log_entry["status"] == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert log_entry["version"] == "test-version"
    assert isinstance(log_entry["duration_ms"], float)
    assert log_entry["duration_ms"] >= 0
