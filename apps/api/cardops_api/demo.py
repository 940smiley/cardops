from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select

from cardops_api.card_service import create_card
from cardops_api.config import get_settings
from cardops_api.database import get_session_factory, init_db
from cardops_api.image_service import register_directory, scan_directory
from cardops_api.models import CardInstance, DirectoryRoot, ImageAsset
from cardops_api.schemas import CardCreate, DirectorySelectRequest
from cardops_api.settings_service import get_or_create_settings

DEMO_CARDS = [
    {
        "slug": "baseball-star-1991",
        "sport": "baseball",
        "player": "Alex Rivera",
        "team": "Chicago Lakes",
        "manufacturer": "Northstar",
        "brand": "Stadium Line",
        "set_name": "Stadium Line",
        "set_year": 1991,
        "card_number": "42",
        "estimated_value": 8.0,
        "tags": ["demo", "baseball"],
    },
    {
        "slug": "football-rookie-2020",
        "sport": "football",
        "player": "Marcus Hale",
        "team": "Dallas Range",
        "manufacturer": "Summit",
        "brand": "Rookie Focus",
        "set_name": "Rookie Focus",
        "set_year": 2020,
        "card_number": "117",
        "rookie": True,
        "estimated_value": 18.0,
        "tags": ["demo", "football", "rookie"],
    },
    {
        "slug": "basketball-graded-2018",
        "sport": "basketball",
        "player": "Jordan Cole",
        "team": "Seattle Sound",
        "manufacturer": "Apex",
        "brand": "Chrome Court",
        "set_name": "Chrome Court",
        "set_year": 2018,
        "card_number": "9",
        "raw_or_graded": "graded",
        "grading_company": "PSA",
        "grade": "9",
        "estimated_value": 42.0,
        "tags": ["demo", "basketball", "graded"],
    },
    {
        "slug": "tcg-serial-2023",
        "sport": "tcg",
        "player": "Ember Lynx",
        "team": None,
        "manufacturer": "CardOps Demo",
        "brand": "Creature League",
        "set_name": "Crystal Trails",
        "set_year": 2023,
        "card_number": "CL-88",
        "parallel": "Blue Crystal",
        "serial_number_current": 12,
        "serial_number_total": 99,
        "estimated_value": 28.0,
        "tags": ["demo", "tcg", "serial-numbered"],
    },
    {
        "slug": "uncertain-facsimile",
        "sport": "baseball",
        "player": "Terry Stone",
        "team": "Unknown",
        "manufacturer": "Heritage House",
        "brand": "Classic Ink",
        "set_name": "Classic Ink",
        "set_year": 1987,
        "card_number": None,
        "autograph": False,
        "condition_notes": "Printed facsimile signature example. Needs back image review.",
        "confidence": 0.42,
        "processing_status": "needs_review",
        "estimated_value": 3.0,
        "tags": ["demo", "uncertain", "facsimile-signature"],
    },
]


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _draw_card(path: Path, card: dict, side: str, accent: tuple[int, int, int]) -> None:
    image = Image.new("RGB", (900, 1260), (246, 248, 250))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((60, 60, 840, 1200), radius=34, fill=(255, 255, 255), outline=(40, 48, 54), width=8)
    draw.rectangle((60, 60, 840, 250), fill=accent)
    title = str(card["player"]) if side == "front" else f"{card['set_year']} {card['set_name']}"
    draw.text((95, 105), title, fill=(255, 255, 255), font=_font(42))
    draw.text((95, 180), str(card.get("team") or card["brand"]), fill=(235, 248, 255), font=_font(28))
    if side == "front":
        draw.ellipse((250, 380, 650, 780), fill=(230, 237, 242), outline=accent, width=10)
        draw.text((315, 535), "DEMO", fill=accent, font=_font(54))
        if card.get("rookie"):
            draw.rounded_rectangle((95, 300, 260, 370), radius=12, fill=(250, 204, 21))
            draw.text((128, 318), "RC", fill=(31, 41, 55), font=_font(34))
        if card["slug"] == "uncertain-facsimile":
            draw.line((225, 900, 690, 810), fill=(30, 64, 175), width=7)
            draw.text((240, 915), "printed signature", fill=(30, 64, 175), font=_font(24))
    else:
        body = [
            f"Manufacturer: {card['manufacturer']}",
            f"Brand: {card['brand']}",
            f"Set: {card['set_name']}",
            f"Card No: {card.get('card_number') or 'unreadable'}",
            f"Year: {card['set_year']}",
        ]
        if card.get("serial_number_current"):
            body.append(f"Serial: {card['serial_number_current']}/{card['serial_number_total']}")
        for index, line in enumerate(body):
            draw.text((110, 340 + index * 72), line, fill=(31, 41, 55), font=_font(30))
        draw.rectangle((120, 900, 780, 1040), fill=(241, 245, 249), outline=(148, 163, 184), width=3)
        draw.text((160, 950), "Generated demo fixture", fill=(71, 85, 105), font=_font(30))
    image.save(path, "PNG")


def create_demo_images(images_dir: Path) -> None:
    images_dir.mkdir(parents=True, exist_ok=True)
    accents = [(15, 118, 110), (180, 83, 9), (37, 99, 235), (126, 34, 206), (75, 85, 99)]
    for card, accent in zip(DEMO_CARDS, accents, strict=True):
        _draw_card(images_dir / f"{card['slug']}_front.png", card, "front", accent)
        _draw_card(images_dir / f"{card['slug']}_back.png", card, "back", accent)
    shutil.copyfile(
        images_dir / "baseball-star-1991_front.png",
        images_dir / "baseball-star-1991_front_duplicate.png",
    )


def seed_demo(force: bool = False) -> None:
    init_db()
    settings = get_settings()
    images_dir = settings.demo_dir / "images"
    create_demo_images(images_dir)

    session_factory = get_session_factory()
    with session_factory() as session:
        if force:
            session.query(ImageAsset).delete()
            session.query(DirectoryRoot).delete()
            session.query(CardInstance).delete()
            session.commit()

        if session.scalar(select(CardInstance).limit(1)) is None:
            for card_data in DEMO_CARDS:
                payload_data = {
                    key: value
                    for key, value in card_data.items()
                    if key not in {"slug"} and value is not None
                }
                payload_data.setdefault("raw_or_graded", "raw")
                payload_data.setdefault("quantity", 1)
                payload_data.setdefault("confidence", 0.86)
                create_card(session, CardCreate(**payload_data), source_identifier="demo-fixture")

        directory = register_directory(
            session,
            DirectorySelectRequest(path=str(images_dir), label="Demo card images"),
        )
        scan_directory(session, directory.id)


def seed_if_needed() -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        if not get_or_create_settings(session).demo_mode:
            return
        existing = session.scalar(select(CardInstance).limit(1))
    if existing is None:
        seed_demo(force=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["seed"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.command == "seed":
        seed_demo(force=args.force)


if __name__ == "__main__":
    main()
