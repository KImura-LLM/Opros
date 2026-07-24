import json

import pytest
from fastapi.responses import JSONResponse

from app import main


class HealthyConnection:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def exec_driver_sql(self, statement: str):
        assert statement == "SELECT 1"


class HealthyEngine:
    def connect(self):
        return HealthyConnection()


class HealthyRedisNativeClient:
    async def ping(self):
        return True


class HealthyRedisClient:
    client = HealthyRedisNativeClient()

    async def connect(self):
        return None


class BrokenEngine:
    def connect(self):
        raise ConnectionError("database unavailable")


class BrokenRedisClient:
    @property
    def client(self):
        raise ConnectionError("redis unavailable")

    async def connect(self):
        raise ConnectionError("redis unavailable")


@pytest.mark.asyncio
async def test_liveness_does_not_depend_on_external_services():
    response = await main.health_check()

    assert response["status"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_is_ok_when_dependencies_respond(monkeypatch):
    monkeypatch.setattr(main, "engine", HealthyEngine())
    monkeypatch.setattr(main, "redis_client", HealthyRedisClient())

    response = await main.readiness_check()

    assert response["status"] == "ready"
    assert response["dependencies"] == {"postgres": "ok", "redis": "ok"}


@pytest.mark.asyncio
async def test_readiness_returns_503_without_dependencies(monkeypatch):
    monkeypatch.setattr(main, "engine", BrokenEngine())
    monkeypatch.setattr(main, "redis_client", BrokenRedisClient())

    response = await main.readiness_check()

    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
    assert json.loads(response.body)["status"] == "not_ready"
