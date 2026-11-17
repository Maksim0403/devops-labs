import json

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_http_metrics(
    client: AsyncClient,
) -> None:
    await client.get("/version")
    response = await client.get("/metrics")

    assert response.status_code == status.HTTP_200_OK
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text
    assert 'endpoint="/version"' in response.text


@pytest.mark.asyncio
async def test_requests_are_logged_as_json_with_required_fields(
    client: AsyncClient, capsys: pytest.CaptureFixture[str]
) -> None:
    await client.get("/version")

    log_entry = json.loads(capsys.readouterr().out.strip().splitlines()[-1])

    assert log_entry["timestamp"]
    assert log_entry["level"] == "info"
    assert log_entry["message"] == "HTTP request"
    assert log_entry["method"] == "GET"
    assert log_entry["route"] == "/version"
    assert log_entry["status"] == status.HTTP_200_OK
    assert log_entry["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_fail_endpoint_returns_and_logs_server_error(
    client: AsyncClient, capsys: pytest.CaptureFixture[str]
) -> None:
    response = await client.get("/fail")

    log_entry = json.loads(capsys.readouterr().out.strip().splitlines()[-1])

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert log_entry["route"] == "/fail"
    assert log_entry["status"] == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert log_entry["level"] == "error"
