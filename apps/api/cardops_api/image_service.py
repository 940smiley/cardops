from __future__ import annotations

import fnmatch
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from cardops_api.audit import add_audit_log
from cardops_api.config import get_settings
from cardops_api.filesystem_service import (
    FilesystemValidationError,
    ensure_unique_root,
    normalized_path_key,
    validate_directory_path,
)
from cardops_api.models import DirectoryRoot, ImageAsset, utc_now

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic"}


DirectoryValidationError = FilesystemValidationError


def _to_dt(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=UTC)


def validate_local_directory(path_text: str) -> Path:
    path, _path_key = validate_directory_path(path_text)
    return path


def is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def register_directory(session: Session, payload: Any) -> DirectoryRoot:
    root_path, path_key = validate_directory_path(payload.path)
    existing = session.scalar(select(DirectoryRoot).where(DirectoryRoot.normalized_path_key == path_key))
    if existing is None:
        existing = session.scalar(select(DirectoryRoot).where(DirectoryRoot.path == str(root_path)))
    if existing is not None:
        if existing.revoked_at is None:
            raise DirectoryValidationError("Directory is already configured.")
        if existing.normalized_path_key and existing.normalized_path_key != path_key:
            ensure_unique_root(session, path_key, ignore_id=existing.id)
        existing.path = str(root_path)
        existing.normalized_path_key = path_key
        existing.revoked_at = None
        existing.label = payload.label
        existing.recursive = payload.recursive
        existing.exclude_patterns = payload.exclude_patterns
        existing.allow_symlinks = payload.allow_symlinks
        session.add(existing)
        add_audit_log(
            session,
            "directory.reactivated",
            entity_type="directory_root",
            entity_id=existing.id,
            details={"path": str(root_path)},
        )
        session.commit()
        session.refresh(existing)
        return existing

    directory = DirectoryRoot(
        path=str(root_path),
        normalized_path_key=path_key,
        label=payload.label,
        recursive=payload.recursive,
        exclude_patterns=payload.exclude_patterns,
        allow_symlinks=payload.allow_symlinks,
    )
    session.add(directory)
    session.flush()
    add_audit_log(
        session,
        "directory.registered",
        entity_type="directory_root",
        entity_id=directory.id,
        details={"path": str(root_path)},
    )
    session.commit()
    session.refresh(directory)
    return directory


def iter_candidate_images(directory: DirectoryRoot) -> list[Path]:
    root = Path(directory.path).resolve()
    pattern = "**/*" if directory.recursive else "*"
    files: list[Path] = []
    for path in root.glob(pattern):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        relative = path.relative_to(root).as_posix()
        if any(fnmatch.fnmatch(relative, pattern) for pattern in directory.exclude_patterns):
            continue
        if path.is_symlink() and not directory.allow_symlinks:
            continue
        if not directory.allow_symlinks and not is_within_root(path, root):
            continue
        files.append(path)
    return sorted(files)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def average_hash(image: Image.Image) -> str:
    gray = ImageOps.grayscale(image).resize((8, 8))
    pixels = list(gray.getdata())
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if pixel >= avg else "0" for pixel in pixels)
    return f"{int(bits, 2):016x}"


def generate_thumbnail(image: Image.Image, image_id: str) -> str:
    settings = get_settings()
    settings.thumbnail_dir.mkdir(parents=True, exist_ok=True)
    thumbnail = image.copy()
    thumbnail.thumbnail((320, 448))
    output = settings.thumbnail_dir / f"{image_id}.jpg"
    if thumbnail.mode not in {"RGB", "L"}:
        thumbnail = thumbnail.convert("RGB")
    thumbnail.save(output, format="JPEG", quality=84, optimize=True)
    return str(output)


def _guess_front_back(path: Path) -> str | None:
    name = path.stem.lower()
    if any(token in name for token in ["front", "_f", "-f", "obverse"]):
        return "front"
    if any(token in name for token in ["back", "_b", "-b", "reverse"]):
        return "back"
    return None


def ingest_image(session: Session, directory: DirectoryRoot, path: Path) -> tuple[ImageAsset, bool]:
    root = Path(directory.path).resolve()
    if directory.normalized_path_key is None:
        directory.normalized_path_key = normalized_path_key(root)
        session.add(directory)
    relative = path.resolve().relative_to(root).as_posix()
    stat = path.stat()
    absolute = str(path.resolve())
    existing = session.scalar(select(ImageAsset).where(ImageAsset.absolute_path == absolute))
    is_new = existing is None
    image = existing or ImageAsset(
        id=None,  # type: ignore[arg-type]
        directory_id=directory.id,
        absolute_path=absolute,
        relative_path=relative,
        file_name=path.name,
        extension=path.suffix.lower(),
        file_size=stat.st_size,
        original_location=absolute,
    )
    if image.id is None:
        from cardops_api.models import new_id

        image.id = new_id()

    image.directory_id = directory.id
    image.relative_path = relative
    image.file_name = path.name
    image.extension = path.suffix.lower()
    image.file_size = stat.st_size
    image.created_time = _to_dt(stat.st_ctime)
    image.modified_time = _to_dt(stat.st_mtime)
    image.original_location = absolute
    image.imported_at = utc_now()
    image.front_back_assignment = _guess_front_back(path)
    image.error_message = None

    try:
        image.sha256 = sha256_file(path)
        with Image.open(path) as source:
            exif = source.getexif()
            image.exif_orientation = exif.get(274) if exif else None
            oriented = ImageOps.exif_transpose(source)
            image.width, image.height = oriented.size
            image.perceptual_hash = average_hash(oriented)
            image.thumbnail_path = generate_thumbnail(oriented, image.id)
        image.processing_status = "ingested"
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        image.processing_status = "failed"
        image.error_message = str(exc)

    session.add(image)
    return image, is_new


def mark_duplicates(session: Session) -> None:
    hashes = session.scalars(
        select(ImageAsset.sha256).where(ImageAsset.sha256.is_not(None)).distinct()
    ).all()
    for file_hash in hashes:
        images = session.scalars(select(ImageAsset).where(ImageAsset.sha256 == file_hash)).all()
        status = "duplicate" if len(images) > 1 else "unique"
        for image in images:
            image.duplicate_status = status
            session.add(image)


def scan_directory(session: Session, directory_id: str, *, cancellation_check=lambda: False) -> dict[str, Any]:
    directory = session.get(DirectoryRoot, directory_id)
    if directory is None or directory.revoked_at is not None:
        raise ValueError("Directory is not registered or has been revoked.")

    files = iter_candidate_images(directory)
    result = {"seen": len(files), "created": 0, "updated": 0, "failed": 0, "duplicates": 0}
    for index, path in enumerate(files):
        if cancellation_check():
            result["cancelled_at"] = index
            break
        image, is_new = ingest_image(session, directory, path)
        if image.processing_status == "failed":
            result["failed"] += 1
        elif is_new:
            result["created"] += 1
        else:
            result["updated"] += 1
        if index % 25 == 0:
            session.flush()

    session.flush()
    mark_duplicates(session)
    result["duplicates"] = len(
        session.scalars(select(ImageAsset).where(ImageAsset.duplicate_status == "duplicate")).all()
    )
    add_audit_log(
        session,
        "directory.scanned",
        entity_type="directory_root",
        entity_id=directory.id,
        details=result,
    )
    session.commit()
    return result


def propose_front_back_pairs(session: Session, image_ids: list[str] | None = None) -> list[dict[str, Any]]:
    query = select(ImageAsset).where(ImageAsset.processing_status == "ingested")
    if image_ids:
        query = query.where(ImageAsset.id.in_(image_ids))
    images = session.scalars(query).all()
    by_stem: dict[str, dict[str, ImageAsset]] = {}
    for image in images:
        stem = Path(image.file_name).stem.lower()
        base = (
            stem.replace("_front", "")
            .replace("-front", "")
            .replace("_back", "")
            .replace("-back", "")
            .replace("_f", "")
            .replace("_b", "")
        )
        by_stem.setdefault(base, {})
        if image.front_back_assignment in {"front", "back"}:
            by_stem[base][image.front_back_assignment] = image

    candidates: list[dict[str, Any]] = []
    for pair in by_stem.values():
        if "front" in pair and "back" in pair:
            candidates.append(
                {
                    "front_image_id": pair["front"].id,
                    "back_image_id": pair["back"].id,
                    "confidence": 0.78,
                    "reason": "filename front/back pattern",
                }
            )
    return candidates
