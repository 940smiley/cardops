from __future__ import annotations

from fastapi.testclient import TestClient


def test_settings_runtime_controls_and_direct_export_guard(client: TestClient) -> None:
    initial = client.get("/settings")
    assert initial.status_code == 200
    assert initial.json()["demo_mode"] is False
    assert initial.json()["listing_export_mode"] == "file_upload"
    assert initial.json()["ebay_sync_limit"] == 25
    assert initial.json()["ebay_sync_include_offers"] is True

    updated = client.put(
        "/settings",
        json={
            "demo_mode": True,
            "live_ebay_publishing_enabled": True,
            "physical_file_moves_enabled": True,
            "listing_export_mode": "ebay_direct",
            "ebay_direct_listing_enabled": False,
            "ebay_marketplace_id": "EBAY_US",
            "ebay_merchant_location_key": "CARDOPS_TEST_LOCATION",
            "ebay_payment_policy_id": "pay-1",
            "ebay_return_policy_id": "return-1",
            "ebay_fulfillment_policy_id": "fulfill-1",
            "ebay_sync_limit": 17,
            "ebay_sync_offset": 3,
            "ebay_sync_include_offers": False,
            "default_listing_format": "auction",
            "confidence_threshold": 0.61,
            "tesseract_cmd": "E:\\Apps\\tesseract-ocr\\tesseract.exe",
            "ocr_language": "eng",
            "default_input_dir": "D:\\Cards\\Incoming",
            "default_output_dir": "D:\\Cards\\Exports",
            "default_inventory_path": "D:\\Cards\\Exports\\inventory.csv",
            "default_ebay_export_path": "D:\\Cards\\Exports\\ebay-listings.csv",
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["demo_mode"] is True
    assert body["live_ebay_publishing_enabled"] is True
    assert body["physical_file_moves_enabled"] is True
    assert body["listing_export_mode"] == "ebay_direct"
    assert body["ebay_direct_listing_enabled"] is False
    assert body["ebay_sync_limit"] == 17
    assert body["ebay_sync_offset"] == 3
    assert body["ebay_sync_include_offers"] is False
    assert body["default_listing_format"] == "auction"
    assert body["confidence_threshold"] == 0.61
    assert body["tesseract_cmd"] == "E:\\Apps\\tesseract-ocr\\tesseract.exe"
    assert body["ocr_language"] == "eng"
    assert body["default_ebay_export_path"] == "D:\\Cards\\Exports\\ebay-listings.csv"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["demo_mode"] is True

    preview = client.post("/exports/listings")
    assert preview.status_code == 200
    assert preview.json()["delivery_mode"] == "ebay_direct_preview"
    assert "No live requests were sent" in preview.json()["message"]

    armed = client.put(
        "/settings",
        json={"ebay_direct_listing_enabled": True, "live_ebay_publishing_enabled": True},
    )
    assert armed.status_code == 200

    blocked = client.post("/exports/listings")
    assert blocked.status_code == 409
    assert "Connect eBay" in blocked.json()["detail"]


def test_ebay_sync_uses_saved_defaults(client: TestClient, monkeypatch) -> None:
    update = client.put(
        "/settings",
        json={
            "ebay_sync_limit": 7,
            "ebay_sync_offset": 4,
            "ebay_sync_include_offers": False,
        },
    )
    assert update.status_code == 200
    calls = {}

    def fake_inventory_items(*, limit: int, offset: int) -> dict[str, object]:
        calls["inventory"] = {"limit": limit, "offset": offset}
        return {
            "total": 1,
            "size": 1,
            "limit": limit,
            "offset": offset,
            "inventoryItems": [{"sku": "cardops-test"}],
        }

    def fake_offer_lookup(*args, **kwargs) -> dict[str, object]:
        raise AssertionError("Offer lookup should be skipped when ebay_sync_include_offers is false.")

    monkeypatch.setattr("cardops_api.routes.get_inventory_items", fake_inventory_items)
    monkeypatch.setattr("cardops_api.routes.get_offers_for_inventory_items", fake_offer_lookup)

    response = client.post("/ebay/sync")

    assert response.status_code == 200
    body = response.json()
    assert calls["inventory"] == {"limit": 7, "offset": 4}
    assert body["state"] == "synced"
    assert body["offers"] is None
    assert body["sync_config"] == {"limit": 7, "offset": 4, "include_offers": False}
