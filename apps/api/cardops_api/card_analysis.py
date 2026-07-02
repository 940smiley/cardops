from __future__ import annotations

import csv
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any

from cardops_api.config import get_settings
from cardops_api.models import CardInstance, ImageAsset

TITLE_LIMIT = 80
DEFAULT_OCR_TIMEOUT_SECONDS = 20

MANUFACTURERS = [
    "Topps",
    "Panini",
    "Upper Deck",
    "Donruss",
    "Bowman",
    "Fleer",
    "Score",
    "Leaf",
    "O-Pee-Chee",
    "SkyBox",
    "Hoops",
    "Prizm",
    "Select",
    "Mosaic",
    "Optic",
]

SPORT_HINTS = {
    "baseball": ["baseball", "mlb"],
    "basketball": ["basketball", "nba"],
    "football": ["football", "nfl"],
    "hockey": ["hockey", "nhl"],
    "soccer": ["soccer", "futbol", "football club", "fc "],
    "racing": ["nascar", "racing"],
    "wrestling": ["wrestling", "wwe", "aew"],
}

CARD_FIELDS = [
    "sport",
    "set_year",
    "manufacturer",
    "brand",
    "set_name",
    "subset",
    "player",
    "team",
    "card_number",
    "rookie",
    "variation",
    "parallel",
    "serial_number_current",
    "serial_number_total",
    "autograph",
    "relic",
    "grading_company",
    "grade",
    "raw_or_graded",
    "quantity",
    "condition_notes",
    "processing_status",
    "confidence",
    "tags",
]


@dataclass(frozen=True)
class DependencyCheck:
    name: str
    status: str
    detail: str
    path: str | None = None
    version: str | None = None


@dataclass(frozen=True)
class OcrOutput:
    status: str
    engine: str
    text: str
    confidence: float
    lines: list[str] = field(default_factory=list)
    error: str | None = None


def _clean_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _title_case(value: str) -> str:
    words = []
    for word in _clean_space(value).split(" "):
        if word.isupper() and len(word) <= 4:
            words.append(word)
        elif "/" in word:
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:].lower())
    return " ".join(words)


def detect_tesseract(explicit_path: str | None = None) -> DependencyCheck:
    candidates = []
    if explicit_path:
        candidates.append(explicit_path)
    configured = getattr(get_settings(), "tesseract_cmd", None)
    if configured:
        candidates.append(configured)
    default_windows_path = Path("E:/Apps/tesseract-ocr/tesseract.exe")
    if default_windows_path.exists():
        candidates.append(str(default_windows_path))
    detected = shutil.which("tesseract")
    if detected:
        candidates.append(detected)

    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.exists() and shutil.which(candidate) is None:
            continue
        executable = str(path) if path.exists() else candidate
        try:
            result = subprocess.run(
                [executable, "--version"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return DependencyCheck(
                name="Tesseract OCR",
                status="failed",
                detail=str(exc),
                path=executable,
            )
        version = (result.stdout or result.stderr).splitlines()[0] if (result.stdout or result.stderr) else ""
        if result.returncode == 0:
            return DependencyCheck(
                name="Tesseract OCR",
                status="available",
                detail="Tesseract executable responded.",
                path=executable,
                version=version,
            )
        return DependencyCheck(
            name="Tesseract OCR",
            status="failed",
            detail=(result.stderr or result.stdout or "Tesseract exited with an error.").strip(),
            path=executable,
            version=version,
        )

    return DependencyCheck(
        name="Tesseract OCR",
        status="missing_dependency",
        detail="Tesseract was not found on PATH or in CARDOPS_TESSERACT_CMD.",
    )


def detect_dependencies() -> list[DependencyCheck]:
    checks = [
        DependencyCheck(
            name="Python",
            status="available" if shutil.which("python") else "missing_dependency",
            detail="Python is used for the API, worker, and launcher diagnostics.",
            path=shutil.which("python"),
        ),
        DependencyCheck(
            name="uv",
            status="available" if shutil.which("uv") else "missing_dependency",
            detail="uv manages Python dependencies and commands.",
            path=shutil.which("uv"),
        ),
        DependencyCheck(
            name="Node.js",
            status="available" if shutil.which("node") else "missing_dependency",
            detail="Node.js runs the Vite frontend.",
            path=shutil.which("node"),
        ),
        DependencyCheck(
            name="Corepack",
            status="available" if shutil.which("corepack") else "missing_dependency",
            detail="Corepack activates pnpm.",
            path=shutil.which("corepack"),
        ),
        detect_tesseract(),
    ]
    checks.append(
        DependencyCheck(
            name="OpenCV Python",
            status="available" if _module_available("cv2") else "missing_dependency",
            detail="OpenCV preprocessing is optional; Pillow-based ingestion remains available.",
        )
    )
    return checks


def _module_available(module_name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(module_name) is not None


def run_tesseract_ocr(
    image_path: Path,
    *,
    explicit_path: str | None = None,
    lang: str | None = None,
) -> OcrOutput:
    dependency = detect_tesseract(explicit_path)
    if dependency.status != "available" or not dependency.path:
        return OcrOutput(
            status=dependency.status,
            engine="tesseract",
            text="",
            confidence=0.0,
            error=dependency.detail,
        )

    language = lang or getattr(get_settings(), "ocr_language", "eng")
    try:
        result = subprocess.run(
            [dependency.path, str(image_path), "stdout", "--psm", "6", "-l", language],
            capture_output=True,
            text=True,
            timeout=DEFAULT_OCR_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return OcrOutput(
            status="timeout",
            engine="tesseract",
            text="",
            confidence=0.0,
            error=f"Tesseract exceeded {DEFAULT_OCR_TIMEOUT_SECONDS} seconds.",
        )
    except OSError as exc:
        return OcrOutput(status="failed", engine="tesseract", text="", confidence=0.0, error=str(exc))

    text = _clean_space(result.stdout)
    if result.returncode != 0:
        return OcrOutput(
            status="failed",
            engine="tesseract",
            text=text,
            confidence=0.0,
            error=(result.stderr or "Tesseract exited with an error.").strip(),
        )
    lines = [_clean_space(line) for line in result.stdout.splitlines() if _clean_space(line)]
    confidence = 0.55 if text else 0.0
    return OcrOutput(status="succeeded", engine="tesseract", text=text, confidence=confidence, lines=lines)


def fallback_text_from_image(image: ImageAsset) -> OcrOutput:
    stem = Path(image.file_name).stem
    text = _clean_space(re.sub(r"[_-]+", " ", stem))
    return OcrOutput(
        status="fallback",
        engine="filename",
        text=text,
        confidence=0.25 if text else 0.0,
        lines=[text] if text else [],
        error="Tesseract text was unavailable; using filename-only hints.",
    )


def _first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1) if match else None


def _detect_sport(text_lower: str) -> tuple[str | None, float]:
    for sport, hints in SPORT_HINTS.items():
        if any(hint in text_lower for hint in hints):
            return sport, 0.8
    return None, 0.0


def _detect_manufacturer(text: str) -> tuple[str | None, float]:
    lower = text.lower()
    for manufacturer in MANUFACTURERS:
        if manufacturer.lower() in lower:
            return manufacturer, 0.85
    return None, 0.0


def _detect_player(lines: list[str], text: str) -> tuple[str | None, float]:
    blacklist = {
        "rookie",
        "rc",
        "baseball",
        "basketball",
        "football",
        "hockey",
        "soccer",
        "topps",
        "panini",
        "donruss",
        "bowman",
        "upper deck",
        "prizm",
        "chrome",
        "select",
        "mosaic",
        "optic",
        "front",
        "back",
        "obverse",
        "reverse",
    }
    candidates = []
    for raw in lines or [text]:
        value = _clean_space(re.sub(r"[^A-Za-z .'-]", " ", raw))
        words = [word for word in value.split() if len(word) > 1]
        words = [word for word in words if word.lower() not in blacklist]
        if not 2 <= len(words) <= 4:
            continue
        candidate = " ".join(words)
        lowered = candidate.lower()
        if any(token in lowered for token in blacklist):
            continue
        candidates.append(candidate)
    if candidates:
        return _title_case(candidates[0]), 0.55
    return None, 0.0


def normalize_card_text(
    text: str,
    *,
    source_identifier: str,
    ocr_confidence: float,
    confidence_threshold: float | None = None,
) -> dict[str, Any]:
    normalized_text = _clean_space(text)
    lower = normalized_text.lower()
    lines = [_clean_space(line) for line in re.split(r"[\r\n|]+", text) if _clean_space(line)]
    candidate: dict[str, Any] = {
        "quantity": 1,
        "raw_or_graded": "raw",
        "rookie": False,
        "autograph": False,
        "relic": False,
        "processing_status": "needs_review",
        "tags": ["local-identification"],
    }
    evidence: list[dict[str, Any]] = []

    def set_field(field_name: str, value: Any, confidence: float, source: str = "local_heuristic") -> None:
        if value in (None, ""):
            return
        candidate[field_name] = value
        evidence.append(
            {
                "field_name": field_name,
                "value": str(value),
                "source_type": source,
                "source_identifier": source_identifier,
                "confidence": round(confidence, 3),
            }
        )

    year = _first_match(r"\b(18\d{2}|19\d{2}|20\d{2}|21\d{2})\b", normalized_text)
    if year:
        set_field("set_year", int(year), min(0.9, 0.55 + ocr_confidence / 2))

    sport, sport_confidence = _detect_sport(lower)
    set_field("sport", sport, sport_confidence)

    manufacturer, manufacturer_confidence = _detect_manufacturer(normalized_text)
    set_field("manufacturer", manufacturer, manufacturer_confidence)
    if manufacturer:
        set_field("brand", manufacturer, 0.7)

    card_number = (
        _first_match(r"(?:#|no\.?|number)\s*([A-Z0-9-]{1,12})\b", normalized_text)
        or _first_match(r"\bcard\s+([A-Z0-9-]{1,12})\b", normalized_text)
    )
    set_field("card_number", card_number, 0.65)

    serial_match = re.search(r"\b(\d{1,6})\s*/\s*(\d{1,6})\b", normalized_text)
    if serial_match:
        set_field("serial_number_current", int(serial_match.group(1)), 0.85)
        set_field("serial_number_total", int(serial_match.group(2)), 0.85)

    if re.search(r"\b(RC|rookie)\b", normalized_text, flags=re.IGNORECASE):
        set_field("rookie", True, 0.8)
    if re.search(r"\b(auto|autograph|signed)\b", normalized_text, flags=re.IGNORECASE):
        set_field("autograph", True, 0.75)
    if re.search(r"\b(relic|patch|jersey|memorabilia)\b", normalized_text, flags=re.IGNORECASE):
        set_field("relic", True, 0.75)

    grade_match = re.search(r"\b(PSA|BGS|SGC|CGC)\s*(\d+(?:\.\d)?)\b", normalized_text, flags=re.IGNORECASE)
    if grade_match:
        company = grade_match.group(1).upper()
        set_field("raw_or_graded", "graded", 0.9)
        set_field("grading_company", company, 0.9)
        set_field("grade", grade_match.group(2), 0.9)

    for parallel_hint in ["refractor", "silver", "gold", "red", "blue", "green", "mosaic", "prizm"]:
        if re.search(rf"\b{re.escape(parallel_hint)}\b", lower):
            set_field("parallel", _title_case(parallel_hint), 0.55)
            break

    player, player_confidence = _detect_player(lines, normalized_text)
    set_field("player", player, player_confidence)

    filled_confidences = [entry["confidence"] for entry in evidence]
    overall = min(0.95, sum(filled_confidences) / max(len(CARD_FIELDS), 1)) if filled_confidences else 0.0
    overall = max(overall, min(0.65, ocr_confidence * 0.8)) if evidence else overall
    candidate["confidence"] = round(overall, 3)
    threshold = confidence_threshold if confidence_threshold is not None else get_settings().confidence_threshold
    if candidate["confidence"] >= threshold and not {"player", "set_year", "card_number"} - candidate.keys():
        candidate["processing_status"] = "approved"

    unresolved = [
        field_name
        for field_name in [
            "sport",
            "set_year",
            "manufacturer",
            "player",
            "team",
            "set_name",
            "card_number",
            "condition_notes",
        ]
        if candidate.get(field_name) in (None, "", [])
    ]
    return {
        "candidate": {key: candidate.get(key) for key in CARD_FIELDS if key in candidate},
        "confidence": candidate["confidence"],
        "unresolved_fields": unresolved,
        "evidence": evidence,
        "normalized_text": normalized_text,
    }


def identify_image(
    image: ImageAsset,
    *,
    tesseract_cmd: str | None = None,
    ocr_language: str | None = None,
    confidence_threshold: float | None = None,
) -> dict[str, Any]:
    path = Path(image.absolute_path)
    ocr = run_tesseract_ocr(path, explicit_path=tesseract_cmd, lang=ocr_language)
    fallback = fallback_text_from_image(image)
    if not ocr.text:
        text = fallback.text
        ocr_payload = fallback
    else:
        text_parts = [ocr.text]
        if fallback.text and fallback.text.lower() not in ocr.text.lower():
            text_parts.append(fallback.text)
        text = "\n".join(text_parts)
        ocr_payload = ocr

    analysis = normalize_card_text(
        text,
        source_identifier=image.id,
        ocr_confidence=ocr_payload.confidence,
        confidence_threshold=confidence_threshold,
    )
    return {
        "image_id": image.id,
        "source_image": image.absolute_path,
        "ocr": {
            "status": ocr_payload.status,
            "engine": ocr_payload.engine,
            "text": ocr_payload.text,
            "confidence": ocr_payload.confidence,
            "lines": ocr_payload.lines,
            "error": ocr_payload.error,
        },
        **analysis,
    }


def decimal_to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def estimate_price(card: CardInstance) -> dict[str, Any]:
    manual_value = decimal_to_float(card.estimated_value)
    if manual_value is not None:
        return {
            "recommended_price": round(manual_value, 2),
            "source": "MANUAL_VALUE",
            "configured": True,
            "caution": None,
        }
    if get_settings().demo_mode:
        seed = "|".join(str(getattr(card, name) or "") for name in ["player", "set_year", "brand", "card_number"])
        amount = 1.99 + (sum(ord(ch) for ch in seed) % 3500) / 100
        return {
            "recommended_price": round(amount, 2),
            "source": "MockPricingProvider",
            "configured": True,
            "caution": "Demo estimate only; not verified sold data.",
        }
    return {
        "recommended_price": None,
        "source": "not_configured",
        "configured": False,
        "caution": "No configured pricing source and no manual estimated value.",
    }


def build_ebay_title(card: CardInstance) -> dict[str, Any]:
    parts = [
        str(card.set_year) if card.set_year else None,
        card.brand or card.manufacturer,
        card.set_name,
        card.player,
        f"#{card.card_number}" if card.card_number else None,
        card.parallel,
        "RC" if card.rookie else None,
        "Auto" if card.autograph else None,
        "Relic" if card.relic else None,
        f"{card.grading_company} {card.grade}" if card.grading_company and card.grade else None,
    ]
    title = _clean_space(" ".join(part for part in parts if part))
    warnings = []
    if not title:
        title = f"Sports Card {card.internal_sku}"
        warnings.append("Title has insufficient card identity fields.")
    if len(title) > TITLE_LIMIT:
        title = title[:TITLE_LIMIT].rstrip()
        warnings.append("Title was trimmed to eBay's 80-character limit.")
    return {"title": title, "length": len(title), "limit": TITLE_LIMIT, "warnings": warnings}


def recommend_listing(
    card: CardInstance,
    *,
    default_listing_format: str = "fixed_price",
    confidence_threshold: float = 0.72,
) -> dict[str, Any]:
    price = estimate_price(card)
    title = build_ebay_title(card)
    incomplete = not card.player or not card.set_year or not card.card_number
    low_confidence = card.confidence is not None and card.confidence < confidence_threshold
    recommended_price = price["recommended_price"]
    if incomplete or low_confidence:
        listing_format = "needs_review"
        lot_assignment = "identity-review"
    elif recommended_price is not None and recommended_price < 8:
        listing_format = "auction_or_lot"
        lot_assignment = "low-value-lot"
    else:
        listing_format = default_listing_format
        lot_assignment = "configured-lot" if default_listing_format == "auction_or_lot" else "single-card"
    warnings = list(title["warnings"])
    if low_confidence:
        warnings.append(f"Card confidence is below the configured {confidence_threshold:.2f} threshold.")
    return {
        **title,
        "warnings": warnings,
        "recommended_listing_format": listing_format,
        "recommended_price": recommended_price,
        "pricing_source": price["source"],
        "pricing_configured": price["configured"],
        "price_caution": price["caution"],
        "lot_assignment": lot_assignment,
        "data_source": "CardOps deterministic local recommendation",
    }


def listing_csv_rows(
    cards: list[CardInstance],
    *,
    default_listing_format: str = "fixed_price",
    confidence_threshold: float = 0.72,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for card in cards:
        listing = recommend_listing(
            card,
            default_listing_format=default_listing_format,
            confidence_threshold=confidence_threshold,
        )
        rows.append(
            {
                "Internal SKU": card.internal_sku,
                "Title": listing["title"],
                "Recommended Format": listing["recommended_listing_format"],
                "Recommended Price": listing["recommended_price"] or "",
                "Lot Assignment": listing["lot_assignment"],
                "Sport": card.sport or "",
                "Player": card.player or "",
                "Team": card.team or "",
                "Year": card.set_year or "",
                "Manufacturer": card.manufacturer or "",
                "Brand": card.brand or "",
                "Set": card.set_name or "",
                "Card Number": card.card_number or "",
                "Rookie": "yes" if card.rookie else "no",
                "Autograph": "yes" if card.autograph else "no",
                "Relic": "yes" if card.relic else "no",
                "Condition Notes": card.condition_notes or "",
                "Confidence": card.confidence if card.confidence is not None else "",
                "Data Source": listing["data_source"],
                "Warnings": "; ".join(listing["warnings"] or []),
            }
        )
    return rows


def render_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()
