from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_card_records_provenance(client: TestClient) -> None:
    response = client.post(
        "/cards",
        json={
            "sport": "baseball",
            "player": "Test Player",
            "team": "Test Team",
            "manufacturer": "Demo",
            "set_name": "Local Test",
            "set_year": 1999,
            "card_number": "7",
            "estimated_value": 4.5,
            "tags": ["test"],
        },
    )

    assert response.status_code == 200
    card = response.json()
    assert card["internal_sku"].startswith("COA-")
    assert card["player"] == "Test Player"

    provenance = client.get(f"/cards/{card['id']}/provenance")
    assert provenance.status_code == 200
    fields = {record["field_name"] for record in provenance.json()}
    assert "player" in fields
    assert "estimated_value" in fields
