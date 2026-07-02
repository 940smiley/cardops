from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw


def _make_image(path: Path, label: str, color: tuple[int, int, int]) -> None:
    image = Image.new("RGB", (300, 420), color)
    draw = ImageDraw.Draw(image)
    draw.text((28, 190), label, fill=(255, 255, 255))
    image.save(path, "PNG")


def test_directory_scan_ingests_images_and_detects_duplicates(
    client: TestClient, tmp_path: Path
) -> None:
    image_dir = tmp_path / "cards"
    image_dir.mkdir()
    front = image_dir / "sample_front.png"
    back = image_dir / "sample_back.png"
    duplicate = image_dir / "sample_front_duplicate.png"
    _make_image(front, "front", (15, 118, 110))
    _make_image(back, "back", (180, 83, 9))
    shutil.copyfile(front, duplicate)

    selected = client.post(
        "/directories/select",
        json={"path": str(image_dir), "label": "Test scan", "recursive": True},
    )
    assert selected.status_code == 200
    directory_id = selected.json()["id"]

    job = client.post("/directories/scan", json={"directory_id": directory_id, "run_inline": True})
    assert job.status_code == 200
    body = job.json()
    assert body["status"] == "succeeded"
    assert body["result"]["seen"] == 3
    assert body["result"]["created"] == 3

    images = client.get("/images")
    assert images.status_code == 200
    rows = images.json()
    assert len(rows) == 3
    assert {row["front_back_assignment"] for row in rows} >= {"front", "back"}
    duplicates = [row for row in rows if row["duplicate_status"] == "duplicate"]
    assert len(duplicates) == 2
    assert all(row["thumbnail_path"] for row in rows)

    pairs = client.post("/images/pair", json={})
    assert pairs.status_code == 200
    assert pairs.json()[0]["reason"] == "filename front/back pattern"


def test_root_management_prevents_duplicates_and_reports_counts(
    client: TestClient, tmp_path: Path
) -> None:
    image_dir = tmp_path / "cards"
    image_dir.mkdir()
    _make_image(image_dir / "card_front.png", "front", (15, 118, 110))

    selected = client.post(
        "/directories/select",
        json={"path": str(image_dir), "label": "Inbox", "recursive": True},
    )
    assert selected.status_code == 200
    directory = selected.json()
    assert directory["status"] == "active"
    assert directory["normalized_path_key"]

    duplicate = client.post(
        "/directories/select",
        json={"path": f"{image_dir}{Path('/').anchor}", "label": "Duplicate", "recursive": True},
    )
    assert duplicate.status_code == 400
    assert "already configured" in duplicate.json()["detail"]

    scan = client.post("/directories/scan", json={"directory_id": directory["id"], "run_inline": True})
    assert scan.status_code == 200

    roots = client.get("/directories")
    assert roots.status_code == 200
    body = roots.json()
    assert len(body) == 1
    assert body[0]["image_count"] == 1
    assert body[0]["pending_identification_count"] == 1


def test_root_removal_never_deletes_physical_files_and_can_remove_index(
    client: TestClient, tmp_path: Path
) -> None:
    image_dir = tmp_path / "cards"
    image_dir.mkdir()
    image_path = image_dir / "card_front.png"
    _make_image(image_path, "front", (15, 118, 110))

    selected = client.post(
        "/directories/select",
        json={"path": str(image_dir), "label": "Inbox", "recursive": True},
    )
    directory_id = selected.json()["id"]
    scan = client.post("/directories/scan", json={"directory_id": directory_id, "run_inline": True})
    assert scan.status_code == 200

    blocked = client.request("DELETE", f"/directories/{directory_id}", json={"confirmed": False})
    assert blocked.status_code == 409

    removed = client.request(
        "DELETE",
        f"/directories/{directory_id}",
        json={"confirmed": True, "remove_index_records": True},
    )
    assert removed.status_code == 200
    assert removed.json()["status"] == "revoked"
    assert removed.json()["image_count"] == 0
    assert image_path.exists()

    images = client.get("/images")
    assert images.status_code == 200
    assert images.json() == []


def test_root_status_detects_missing_directory(client: TestClient, tmp_path: Path) -> None:
    image_dir = tmp_path / "cards"
    image_dir.mkdir()
    selected = client.post(
        "/directories/select",
        json={"path": str(image_dir), "label": "Inbox", "recursive": True},
    )
    assert selected.status_code == 200
    shutil.rmtree(image_dir)

    roots = client.get("/directories")

    assert roots.status_code == 200
    assert roots.json()[0]["status"] == "missing"
