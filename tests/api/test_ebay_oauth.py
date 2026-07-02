from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cardops_api.ebay_oauth import build_authorization_url, github_pages_callback_url
from cardops_api.ebay_service import EbayApiError, _request_token, get_offers, get_offers_for_inventory_items
from fastapi.testclient import TestClient


def test_github_pages_callback_url() -> None:
    assert github_pages_callback_url() == "https://940smiley.github.io/cardops/ebay/callback/"


def test_build_authorization_url_uses_supplied_redirect_value() -> None:
    url = build_authorization_url(
        client_id="client",
        redirect_value="Example_RUNAME",
        scopes=["scope-a", "scope-b"],
        environment="production",
        state="state-1",
    )
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.netloc == "auth.ebay.com"
    assert query["redirect_uri"] == ["Example_RUNAME"]
    assert query["client_id"] == ["client"]
    assert query["state"] == ["state-1"]


def test_ebay_callback_records_code_metadata(client: TestClient) -> None:
    response = client.get("/ebay/callback?code=v%5Etest-code&state=cardops-test&expires_in=299")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "received"
    assert body["code"]["present"] is True
    assert body["code"]["sha256"]
    assert body["code"]["prefix"] == "v^test"


def test_ebay_callback_browser_mode_returns_html(client: TestClient) -> None:
    response = client.get("/ebay/callback?code=v%5Etest-code&state=cardops-test&browser=1")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "eBay connection not completed" in response.text
    assert "Open CardOps" in response.text


def test_ebay_token_error_includes_safe_error_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    class Settings:
        ebay_client_id = "client"
        ebay_client_secret = "secret"
        ebay_environment = "production"

    def fake_post(*args: object, **kwargs: object) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": "invalid_grant",
                "error_description": "redirect_uri mismatch",
            },
        )

    monkeypatch.setattr("cardops_api.ebay_service.httpx.post", fake_post)
    with pytest.raises(EbayApiError, match="invalid_grant"):
        _request_token({"grant_type": "authorization_code", "code": "code"}, Settings())  # type: ignore[arg-type]


def test_get_offers_requires_sku() -> None:
    with pytest.raises(ValueError, match="requires a seller SKU"):
        get_offers()


def test_get_offers_for_inventory_items_calls_offer_by_sku(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_get_offers(*, sku: str | None = None, limit: int = 25, offset: int = 0) -> dict[str, object]:
        assert sku is not None
        calls.append(sku)
        return {"offers": [{"sku": sku, "offerId": f"offer-{sku}"}]}

    monkeypatch.setattr("cardops_api.ebay_service.get_offers", fake_get_offers)
    result = get_offers_for_inventory_items({"inventoryItems": [{"sku": "sku-1"}, {"sku": "sku-2"}]})
    assert calls == ["sku-1", "sku-2"]
    assert result["total"] == 2


def test_get_offers_for_inventory_items_classifies_missing_offer(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_offers(*, sku: str | None = None, limit: int = 25, offset: int = 0) -> dict[str, object]:
        raise EbayApiError(
            "eBay API request failed for /sell/inventory/v1/offer with HTTP 404. "
            "errorId=25713, message=This Offer is not available.",
            status_code=404,
        )

    monkeypatch.setattr("cardops_api.ebay_service.get_offers", fake_get_offers)
    result = get_offers_for_inventory_items({"inventoryItems": [{"sku": "inventory-only"}]})
    assert result["errors"] == []
    assert result["inventoryOnlySkus"] == ["inventory-only"]
