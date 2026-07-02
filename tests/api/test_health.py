from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_and_capabilities(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["demo_mode"] is False

    capabilities = client.get("/system/capabilities")
    assert capabilities.status_code == 200
    body = capabilities.json()
    assert body["local_only_mode"] is True
    provider_names = {provider["name"] for provider in body["providers"]}
    assert "MockEbayProvider" in provider_names
    assert "LocalOnlyVisionProvider" in provider_names
