from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.main import app


class _Redis:
    def __init__(self, *, alive: bool) -> None:
        self._alive = alive

    async def ping(self) -> bool:
        if not self._alive:
            raise ConnectionError("redis down")
        return True


class _Session:
    def __init__(self, *, alive: bool) -> None:
        self._alive = alive

    async def execute(self, _statement: object) -> None:
        if not self._alive:
            raise ConnectionError("database down")


def _check(
    monkeypatch: pytest.MonkeyPatch,
    *,
    database: bool,
    redis: bool,
) -> tuple[int, dict[str, str]]:
    async def session() -> AsyncIterator[_Session]:
        yield _Session(alive=database)

    monkeypatch.setattr("app.api.v1.health.get_redis", lambda: _Redis(alive=redis))
    app.dependency_overrides[get_session] = session
    try:
        response = TestClient(app).get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()
    return response.status_code, response.json()


def test_health_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _check(monkeypatch, database=True, redis=True) == (
        200,
        {"status": "ok", "database": "ok", "redis": "ok"},
    )


def test_redis_outage_keeps_api_available(monkeypatch: pytest.MonkeyPatch) -> None:
    code, body = _check(monkeypatch, database=True, redis=False)
    assert code == 200
    assert body["status"] == "degraded"


def test_database_outage_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    code, body = _check(monkeypatch, database=False, redis=True)
    assert code == 503
    assert body["database"] == "down"
