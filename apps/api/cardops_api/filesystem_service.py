from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cardops_api.audit import add_audit_log
from cardops_api.models import DirectoryRoot, FileOperationManifest, ImageAsset, utc_now


class FilesystemValidationError(ValueError):
    pass


def normalize_path(path_text: str) -> Path:
    raw = path_text.strip().strip('"')
    if not raw:
        raise FilesystemValidationError("Directory path is required.")
    if raw.startswith("\\\\"):
        raise FilesystemValidationError("UNC/network paths are not allowed in local mode.")
    try:
        return Path(raw).expanduser().resolve(strict=False)
    except OSError as exc:
        raise FilesystemValidationError(str(exc)) from exc


def normalized_path_key(path: Path) -> str:
    resolved = path.expanduser().resolve(strict=False)
    return os.path.normcase(str(resolved)).replace("\\", "/").rstrip("/")


def validate_directory_path(path_text: str) -> tuple[Path, str]:
    path = normalize_path(path_text)
    if not path.exists():
        raise FilesystemValidationError("Directory does not exist.")
    if not path.is_dir():
        raise FilesystemValidationError("Path is not a directory.")
    try:
        with os.scandir(path):
            pass
    except OSError as exc:
        raise FilesystemValidationError(f"Directory is not readable: {exc}") from exc
    return path, normalized_path_key(path)


def detect_root_status(directory: DirectoryRoot) -> tuple[str, str]:
    if directory.revoked_at is not None:
        return "revoked", "Root is removed from active scanning."
    try:
        path = normalize_path(directory.path)
    except FilesystemValidationError as exc:
        return "invalid", str(exc)
    if not path.exists():
        return "missing", "Root path does not exist."
    if not path.is_dir():
        return "invalid", "Root path is not a directory."
    try:
        with os.scandir(path):
            pass
    except OSError as exc:
        return "unavailable", f"Root is not readable: {exc}"
    current_key = normalized_path_key(path)
    if directory.normalized_path_key and directory.normalized_path_key != current_key:
        return "moved", "Root path resolves differently than the stored normalized key."
    return "active", "Root is available."


def directory_counts(session: Session, directory_id: str) -> dict[str, int]:
    image_count = session.scalar(
        select(func.count()).select_from(ImageAsset).where(ImageAsset.directory_id == directory_id)
    )
    pending_count = session.scalar(
        select(func.count())
        .select_from(ImageAsset)
        .where(ImageAsset.directory_id == directory_id)
        .where(ImageAsset.card_instance_id.is_(None))
        .where(ImageAsset.processing_status.in_(["ingested", "failed"]))
    )
    return {
        "image_count": int(image_count or 0),
        "pending_identification_count": int(pending_count or 0),
    }


def directory_summary(session: Session, directory: DirectoryRoot) -> dict[str, Any]:
    status, status_detail = detect_root_status(directory)
    return {
        "id": directory.id,
        "path": directory.path,
        "normalized_path_key": directory.normalized_path_key,
        "label": directory.label,
        "recursive": directory.recursive,
        "exclude_patterns": directory.exclude_patterns,
        "allow_symlinks": directory.allow_symlinks,
        "created_at": directory.created_at,
        "revoked_at": directory.revoked_at,
        "status": status,
        "status_detail": status_detail,
        **directory_counts(session, directory.id),
    }


def ensure_unique_root(session: Session, path_key: str, *, ignore_id: str | None = None) -> None:
    existing = session.scalar(
        select(DirectoryRoot).where(DirectoryRoot.normalized_path_key == path_key).limit(1)
    )
    if existing is not None and existing.id != ignore_id:
        raise FilesystemValidationError("Directory is already configured.")


def create_file_manifest(
    session: Session,
    *,
    operation_type: str,
    source_root_id: str | None,
    dry_run: bool,
    status: str,
    summary: dict[str, Any],
    entries: list[dict[str, Any]] | None = None,
    error_message: str | None = None,
) -> FileOperationManifest:
    manifest = FileOperationManifest(
        operation_type=operation_type,
        source_root_id=source_root_id,
        dry_run=dry_run,
        status=status,
        summary=summary,
        entries=entries or [],
        error_message=error_message,
        completed_at=utc_now() if status in {"completed", "failed", "skipped"} else None,
    )
    session.add(manifest)
    session.flush()
    add_audit_log(
        session,
        f"file_operation.{operation_type}.{status}",
        entity_type="file_operation_manifest",
        entity_id=manifest.id,
        details=summary,
    )
    return manifest


def open_path_in_file_explorer(path_text: str) -> None:
    path = normalize_path(path_text)
    if not path.exists():
        raise FilesystemValidationError("Path does not exist.")
    system = platform.system().lower()
    if system == "windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif system == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def browse_for_directory() -> str | None:
    if platform.system().lower() != "windows":
        raise FilesystemValidationError("Folder browsing is currently available on Windows local runs.")
    command = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog; "
        "$dialog.Description = 'Select a CardOps Image Inbox root'; "
        "$dialog.ShowNewFolderButton = $false; "
        "if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { "
        "  [Console]::Out.Write($dialog.SelectedPath) "
        "}"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Sta", "-Command", command],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if result.returncode != 0:
        raise FilesystemValidationError((result.stderr or "Folder browse dialog failed.").strip())
    selected = result.stdout.strip()
    return selected or None
