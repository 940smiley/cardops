from __future__ import annotations

import csv
import subprocess
from io import StringIO
from pathlib import Path

from cardops_api.card_analysis import build_ebay_title, normalize_card_text
from cardops_api.models import CardInstance
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw


def _make_image(path: Path, label: str) -> None:
    image = Image.new("RGB", (360, 504), (18, 92, 130))
    draw = ImageDraw.Draw(image)
    draw.text((24, 210), label, fill=(255, 255, 255))
    image.save(path, "PNG")


def test_normalize_card_text_marks_uncertain_fields() -> None:
    result = normalize_card_text(
        "2023 Topps Chrome Mike Trout #27 RC",
        source_identifier="unit-test",
        ocr_confidence=0.25,
    )
    assert result["candidate"]["set_year"] == 2023
    assert result["candidate"]["manufacturer"] == "Topps"
    assert result["candidate"]["player"] == "Mike Trout"
    assert result["candidate"]["rookie"] is True
    assert "team" in result["unresolved_fields"]
    assert result["confidence"] < 0.72


def test_ebay_title_is_capped_to_80_characters() -> None:
    card = CardInstance(
        internal_sku="COA-999999",
        set_year=2023,
        brand="Topps Chrome Sapphire Update Super Long Parallel Name",
        set_name="Baseball Mega Box Refractor Collector Edition",
        player="A Very Long Player Name That Would Break Marketplace Title Limits",
        card_number="US123",
        rookie=True,
        autograph=True,
        relic=False,
        quantity=1,
        raw_or_graded="raw",
        processing_status="manual",
        tags=[],
    )
    title = build_ebay_title(card)
    assert title["length"] <= 80
    assert title["warnings"]


def test_image_identification_create_and_listing_export(client: TestClient, tmp_path: Path) -> None:
    image_dir = tmp_path / "cards"
    image_dir.mkdir()
    image_path = image_dir / "2023_Topps_Chrome_Mike_Trout_27_RC_front.png"
    _make_image(image_path, "2023 Topps Chrome Mike Trout #27 RC")

    selected = client.post("/directories/select", json={"path": str(image_dir), "recursive": True})
    assert selected.status_code == 200
    scan = client.post("/directories/scan", json={"directory_id": selected.json()["id"], "run_inline": True})
    assert scan.status_code == 200
    image_id = client.get("/images").json()[0]["id"]

    identification = client.post(f"/images/{image_id}/identify")
    assert identification.status_code == 200
    body = identification.json()
    assert body["candidate"]["player"] == "Mike Trout"
    assert body["candidate"]["set_year"] == 2023
    assert body["unresolved_fields"]

    created = client.post(f"/images/{image_id}/create-card", json={"overrides": {"team": "Los Angeles Angels"}})
    assert created.status_code == 200
    card = created.json()
    assert card["player"] == "Mike Trout"
    assert card["team"] == "Los Angeles Angels"
    assert card["processing_status"] == "needs_review"

    listing = client.get(f"/cards/{card['id']}/listing-recommendation")
    assert listing.status_code == 200
    assert listing.json()["length"] <= 80
    assert listing.json()["lot_assignment"] in {"single-card", "low-value-lot", "identity-review"}

    exported = client.post("/exports/listings")
    assert exported.status_code == 200
    assert exported.json()["row_count"] == 1
    csv_response = client.get("/exports/listings.csv")
    assert csv_response.status_code == 200
    rows = list(csv.DictReader(StringIO(csv_response.text)))
    assert rows[0]["Player"] == "Mike Trout"


def test_launcher_selftest_runs() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(root / "tools" / "CardOps-Launcher.ps1"),
            "-SelfTest",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert '"status":  "passed"' in result.stdout or '"status":"passed"' in result.stdout
