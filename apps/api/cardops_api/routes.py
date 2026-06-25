from __future__ import annotations

import csv
import html
from io import StringIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from cardops_api.audit import add_audit_log
from cardops_api.card_analysis import (
    detect_dependencies,
    identify_image,
    listing_csv_rows,
    recommend_listing,
    render_csv,
)
from cardops_api.card_service import create_card, update_card
from cardops_api.config import get_settings
from cardops_api.database import get_engine, get_session
from cardops_api.ebay_oauth import build_configured_authorization_url, get_ebay_oauth_config, redact_oauth_code
from cardops_api.ebay_service import (
    EbayApiError,
    EbayAuthorizationRequired,
    clear_ebay_token,
    ebay_token_status,
    exchange_authorization_code,
    get_inventory_items,
    get_offers_for_inventory_items,
)
from cardops_api.filesystem_service import (
    FilesystemValidationError,
    browse_for_directory,
    create_file_manifest,
    directory_counts,
    directory_summary,
    ensure_unique_root,
    normalized_path_key,
    open_path_in_file_explorer,
    validate_directory_path,
)
from cardops_api.image_service import (
    DirectoryValidationError,
    propose_front_back_pairs,
    register_directory,
)
from cardops_api.job_service import enqueue_job, request_cancel, retry_job, run_job_inline
from cardops_api.models import CardInstance, DirectoryRoot, FieldProvenance, ImageAsset, Job, utc_now
from cardops_api.providers import detect_capabilities
from cardops_api.schemas import (
    BulkUpdateRequest,
    CardCreate,
    CardFromImageRequest,
    CardIdentificationResponse,
    CardResponse,
    CardUpdate,
    DependencyStatusResponse,
    DirectoryBrowseResponse,
    DirectoryRemoveRequest,
    DirectoryResponse,
    DirectorySelectRequest,
    DirectoryUpdateRequest,
    ExportResponse,
    HealthResponse,
    ImageAssetResponse,
    JobResponse,
    ListingRecommendationResponse,
    PairCandidate,
    PairRequest,
    PriceSourceClassification,
    ProvenanceResponse,
    ScanDirectoryRequest,
    SettingsResponse,
    SettingsUpdate,
    SystemCapabilitiesResponse,
)
from cardops_api.settings_service import get_or_create_settings, update_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(session: Session = Depends(get_session)) -> HealthResponse:
    with get_engine().connect() as connection:
        connection.exec_driver_sql("select 1")
    settings_record = get_or_create_settings(session)
    return HealthResponse(
        status="ok",
        database="ok",
        demo_mode=settings_record.demo_mode,
        version="0.1.0",
    )


@router.get("/system/capabilities", response_model=SystemCapabilitiesResponse)
def capabilities(session: Session = Depends(get_session)) -> SystemCapabilitiesResponse:
    settings_record = get_or_create_settings(session)
    return SystemCapabilitiesResponse(
        demo_mode=settings_record.demo_mode,
        local_only_mode=settings_record.local_only_mode,
        cloud_ai_enabled=settings_record.cloud_ai_enabled,
        live_ebay_publishing_enabled=settings_record.live_ebay_publishing_enabled,
        physical_file_moves_enabled=settings_record.physical_file_moves_enabled,
        listing_export_mode=settings_record.listing_export_mode,
        ebay_direct_listing_enabled=settings_record.ebay_direct_listing_enabled,
        ebay_sync_limit=settings_record.ebay_sync_limit,
        ebay_sync_offset=settings_record.ebay_sync_offset,
        ebay_sync_include_offers=settings_record.ebay_sync_include_offers,
        default_listing_format=settings_record.default_listing_format,
        confidence_threshold=settings_record.confidence_threshold,
        providers=[provider.__dict__ for provider in detect_capabilities()],
    )


@router.get("/diagnostics/dependencies", response_model=list[DependencyStatusResponse])
def dependency_diagnostics() -> list[DependencyStatusResponse]:
    return [DependencyStatusResponse(**check.__dict__) for check in detect_dependencies()]


@router.get("/settings", response_model=SettingsResponse)
def read_settings(session: Session = Depends(get_session)) -> SettingsResponse:
    return get_or_create_settings(session)


@router.put("/settings", response_model=SettingsResponse)
def write_settings(payload: SettingsUpdate, session: Session = Depends(get_session)) -> SettingsResponse:
    return update_settings(session, **payload.model_dump(exclude_unset=True))


@router.post("/directories/select", response_model=DirectoryResponse)
def select_directory(
    payload: DirectorySelectRequest, session: Session = Depends(get_session)
) -> DirectoryResponse:
    try:
        directory = register_directory(session, payload)
        return DirectoryResponse(**directory_summary(session, directory))
    except DirectoryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/directories/browse", response_model=DirectoryBrowseResponse)
def browse_directory() -> DirectoryBrowseResponse:
    try:
        return DirectoryBrowseResponse(path=browse_for_directory())
    except FilesystemValidationError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


@router.post("/directories/scan", response_model=JobResponse)
def scan_registered_directory(
    payload: ScanDirectoryRequest, session: Session = Depends(get_session)
) -> JobResponse:
    directory = session.get(DirectoryRoot, payload.directory_id)
    if directory is None or directory.revoked_at is not None:
        raise HTTPException(status_code=404, detail="Directory not found or revoked.")
    job = enqueue_job(session, "directory_scan", {"directory_id": directory.id})
    if payload.run_inline:
        job = run_job_inline(session, job)
    return job


@router.get("/directories", response_model=list[DirectoryResponse])
def list_directories(session: Session = Depends(get_session)) -> list[DirectoryResponse]:
    directories = session.scalars(select(DirectoryRoot).order_by(DirectoryRoot.created_at.desc())).all()
    changed = False
    for directory in directories:
        if directory.normalized_path_key is None:
            try:
                directory.normalized_path_key = normalized_path_key(Path(directory.path))
                session.add(directory)
                changed = True
            except FilesystemValidationError:
                pass
    if changed:
        session.commit()
    return [DirectoryResponse(**directory_summary(session, directory)) for directory in directories]


@router.patch("/directories/{directory_id}", response_model=DirectoryResponse)
def update_directory(
    directory_id: str,
    payload: DirectoryUpdateRequest,
    session: Session = Depends(get_session),
) -> DirectoryResponse:
    directory = session.get(DirectoryRoot, directory_id)
    if directory is None:
        raise HTTPException(status_code=404, detail="Directory not found.")
    if payload.path is not None:
        try:
            root_path, path_key = validate_directory_path(payload.path)
            ensure_unique_root(session, path_key, ignore_id=directory.id)
        except FilesystemValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        directory.path = str(root_path)
        directory.normalized_path_key = path_key
        directory.revoked_at = None
    if payload.label is not None:
        directory.label = payload.label.strip() or None
    if payload.recursive is not None:
        directory.recursive = payload.recursive
    if payload.exclude_patterns is not None:
        directory.exclude_patterns = payload.exclude_patterns
    if payload.allow_symlinks is not None:
        directory.allow_symlinks = payload.allow_symlinks
    session.add(directory)
    add_audit_log(
        session,
        "directory.updated",
        entity_type="directory_root",
        entity_id=directory.id,
        details={"path": directory.path},
    )
    session.commit()
    session.refresh(directory)
    return DirectoryResponse(**directory_summary(session, directory))


@router.post("/directories/{directory_id}/reconnect", response_model=DirectoryResponse)
def reconnect_directory(directory_id: str, session: Session = Depends(get_session)) -> DirectoryResponse:
    directory = session.get(DirectoryRoot, directory_id)
    if directory is None:
        raise HTTPException(status_code=404, detail="Directory not found.")
    try:
        root_path, path_key = validate_directory_path(directory.path)
        ensure_unique_root(session, path_key, ignore_id=directory.id)
    except FilesystemValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    directory.path = str(root_path)
    directory.normalized_path_key = path_key
    directory.revoked_at = None
    session.add(directory)
    add_audit_log(
        session,
        "directory.reconnected",
        entity_type="directory_root",
        entity_id=directory.id,
        details={"path": directory.path},
    )
    session.commit()
    session.refresh(directory)
    return DirectoryResponse(**directory_summary(session, directory))


@router.post("/directories/{directory_id}/open")
def open_directory(directory_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    directory = session.get(DirectoryRoot, directory_id)
    if directory is None:
        raise HTTPException(status_code=404, detail="Directory not found.")
    try:
        open_path_in_file_explorer(directory.path)
    except FilesystemValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "opened", "path": directory.path}


@router.delete("/directories/{directory_id}", response_model=DirectoryResponse)
def revoke_directory(
    directory_id: str,
    payload: DirectoryRemoveRequest | None = None,
    session: Session = Depends(get_session),
) -> DirectoryResponse:
    directory = session.get(DirectoryRoot, directory_id)
    if directory is None:
        raise HTTPException(status_code=404, detail="Directory not found.")
    payload = payload or DirectoryRemoveRequest()
    if not payload.confirmed:
        raise HTTPException(status_code=409, detail="Root removal requires explicit confirmation.")
    counts = directory_counts(session, directory.id)
    entries = [
        {
            "image_id": image.id,
            "path": image.absolute_path,
            "action": "remove_index_record" if payload.remove_index_records else "retain_index_record",
        }
        for image in session.scalars(select(ImageAsset).where(ImageAsset.directory_id == directory.id)).all()
    ]
    directory.revoked_at = utc_now()
    session.add(directory)
    if payload.remove_index_records:
        for image in session.scalars(select(ImageAsset).where(ImageAsset.directory_id == directory.id)).all():
            session.delete(image)
    create_file_manifest(
        session,
        operation_type="root_remove",
        source_root_id=directory.id,
        dry_run=False,
        status="completed",
        summary={
            "path": directory.path,
            "physical_files_deleted": False,
            "remove_index_records": payload.remove_index_records,
            **counts,
        },
        entries=entries,
    )
    session.commit()
    session.refresh(directory)
    return DirectoryResponse(**directory_summary(session, directory))


@router.get("/images", response_model=list[ImageAssetResponse])
def list_images(
    duplicate_status: str | None = None,
    status: str | None = None,
    limit: int = 250,
    session: Session = Depends(get_session),
) -> list[ImageAssetResponse]:
    query = select(ImageAsset).order_by(ImageAsset.imported_at.desc()).limit(min(limit, 1000))
    if duplicate_status:
        query = query.where(ImageAsset.duplicate_status == duplicate_status)
    if status:
        query = query.where(ImageAsset.processing_status == status)
    return list(session.scalars(query).all())


@router.get("/images/{image_id}", response_model=ImageAssetResponse)
def get_image(image_id: str, session: Session = Depends(get_session)) -> ImageAssetResponse:
    image = session.get(ImageAsset, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    return image


@router.get("/images/{image_id}/thumbnail")
def get_thumbnail(image_id: str, session: Session = Depends(get_session)) -> FileResponse:
    image = session.get(ImageAsset, image_id)
    if image is None or image.thumbnail_path is None:
        raise HTTPException(status_code=404, detail="Thumbnail not found.")
    path = Path(image.thumbnail_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file not found.")
    return FileResponse(path)


@router.post("/images/{image_id}/process", response_model=JobResponse)
def process_image(image_id: str, session: Session = Depends(get_session)) -> JobResponse:
    image = session.get(ImageAsset, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    return enqueue_job(session, "image_identification", {"image_id": image.id}, max_attempts=1)


@router.post("/images/{image_id}/identify", response_model=CardIdentificationResponse)
def identify_image_now(image_id: str, session: Session = Depends(get_session)) -> CardIdentificationResponse:
    image = session.get(ImageAsset, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    settings_record = get_or_create_settings(session)
    return CardIdentificationResponse(
        **identify_image(
            image,
            tesseract_cmd=settings_record.tesseract_cmd,
            ocr_language=settings_record.ocr_language,
            confidence_threshold=settings_record.confidence_threshold,
        )
    )


@router.post("/images/{image_id}/create-card", response_model=CardResponse)
def create_card_from_image(
    image_id: str,
    payload: CardFromImageRequest | None = None,
    session: Session = Depends(get_session),
) -> CardResponse:
    image = session.get(ImageAsset, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    settings_record = get_or_create_settings(session)
    identification = identify_image(
        image,
        tesseract_cmd=settings_record.tesseract_cmd,
        ocr_language=settings_record.ocr_language,
        confidence_threshold=settings_record.confidence_threshold,
    )
    candidate = identification["candidate"]
    if payload and payload.overrides:
        candidate.update(payload.overrides.model_dump(exclude_unset=True))
    card = create_card(
        session,
        CardCreate(**candidate),
        source_identifier=f"image:{image.id}",
    )
    image.card_instance_id = card.id
    image.processing_status = "identified"
    session.add(image)
    session.commit()
    session.refresh(card)
    return card


@router.post("/images/pair", response_model=list[PairCandidate])
def pair_images(payload: PairRequest, session: Session = Depends(get_session)) -> list[PairCandidate]:
    return propose_front_back_pairs(session, payload.image_ids)


@router.post("/images/bulk-process", response_model=JobResponse)
def bulk_process_images(payload: PairRequest, session: Session = Depends(get_session)) -> JobResponse:
    return enqueue_job(
        session,
        "image_identification",
        {"image_ids": payload.image_ids or []},
        max_attempts=1,
    )


@router.get("/cards", response_model=list[CardResponse])
def list_cards(
    q: str | None = None,
    limit: int = 500,
    session: Session = Depends(get_session),
) -> list[CardResponse]:
    query = select(CardInstance).order_by(CardInstance.created_at.desc()).limit(min(limit, 1000))
    if q:
        like = f"%{q}%"
        query = query.where(
            CardInstance.player.like(like)
            | CardInstance.team.like(like)
            | CardInstance.set_name.like(like)
            | CardInstance.internal_sku.like(like)
        )
    return list(session.scalars(query).all())


@router.post("/cards", response_model=CardResponse)
def create_inventory_card(
    payload: CardCreate, session: Session = Depends(get_session)
) -> CardResponse:
    return create_card(session, payload)


@router.get("/cards/{card_id}", response_model=CardResponse)
def get_card(card_id: str, session: Session = Depends(get_session)) -> CardResponse:
    card = session.get(CardInstance, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found.")
    return card


@router.patch("/cards/{card_id}", response_model=CardResponse)
def patch_card(
    card_id: str, payload: CardUpdate, session: Session = Depends(get_session)
) -> CardResponse:
    card = session.get(CardInstance, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found.")
    return update_card(session, card, payload)


@router.post("/cards/{card_id}/approve", response_model=CardResponse)
def approve_card(card_id: str, session: Session = Depends(get_session)) -> CardResponse:
    card = session.get(CardInstance, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found.")
    card.processing_status = "approved"
    card.updated_at = utc_now()
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


@router.post("/cards/bulk-update", response_model=list[CardResponse])
def bulk_update_cards(
    payload: BulkUpdateRequest, session: Session = Depends(get_session)
) -> list[CardResponse]:
    cards = session.scalars(select(CardInstance).where(CardInstance.id.in_(payload.card_ids))).all()
    for card in cards:
        update_card(session, card, payload.patch)
    return list(cards)


@router.get("/cards/{card_id}/provenance", response_model=list[ProvenanceResponse])
def get_card_provenance(
    card_id: str, session: Session = Depends(get_session)
) -> list[ProvenanceResponse]:
    return list(
        session.scalars(
            select(FieldProvenance)
            .where(FieldProvenance.entity_type == "card_instance")
            .where(FieldProvenance.entity_id == card_id)
            .order_by(FieldProvenance.created_at.desc())
        ).all()
    )


@router.get("/review/identification", response_model=list[CardResponse])
def identification_review_queue(session: Session = Depends(get_session)) -> list[CardResponse]:
    return list(
        session.scalars(
            select(CardInstance)
            .where(CardInstance.processing_status.in_(["needs_review", "manual"]))
            .order_by(CardInstance.created_at.desc())
            .limit(100)
        ).all()
    )


@router.post("/review/{card_id}/resolve", response_model=CardResponse)
def resolve_review(
    card_id: str, payload: CardUpdate, session: Session = Depends(get_session)
) -> CardResponse:
    card = session.get(CardInstance, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found.")
    updated = update_card(session, card, payload)
    updated.processing_status = "approved"
    session.add(updated)
    session.commit()
    session.refresh(updated)
    return updated


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(session: Session = Depends(get_session)) -> list[JobResponse]:
    return list(session.scalars(select(Job).order_by(Job.created_at.desc()).limit(200)).all())


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, session: Session = Depends(get_session)) -> JobResponse:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: str, session: Session = Depends(get_session)) -> JobResponse:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return request_cancel(session, job)


@router.post("/jobs/{job_id}/retry", response_model=JobResponse)
def retry_failed_job(job_id: str, session: Session = Depends(get_session)) -> JobResponse:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return retry_job(session, job)


@router.post("/exports/inventory", response_class=PlainTextResponse)
def export_inventory(session: Session = Depends(get_session)) -> Response:
    cards = session.scalars(select(CardInstance).order_by(CardInstance.internal_sku)).all()
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Internal SKU",
            "Sport",
            "Player",
            "Team",
            "Manufacturer",
            "Brand",
            "Set",
            "Year",
            "Card number",
            "Estimated value",
            "Processing status",
            "Tags",
        ]
    )
    for card in cards:
        writer.writerow(
            [
                card.internal_sku,
                card.sport,
                card.player,
                card.team,
                card.manufacturer,
                card.brand,
                card.set_name,
                card.set_year,
                card.card_number,
                card.estimated_value,
                card.processing_status,
                ",".join(card.tags),
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="cardops-inventory.csv"'},
    )


@router.get("/cards/{card_id}/listing-recommendation", response_model=ListingRecommendationResponse)
def listing_recommendation(
    card_id: str, session: Session = Depends(get_session)
) -> ListingRecommendationResponse:
    card = session.get(CardInstance, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found.")
    settings_record = get_or_create_settings(session)
    return ListingRecommendationResponse(
        **recommend_listing(
            card,
            default_listing_format=settings_record.default_listing_format,
            confidence_threshold=settings_record.confidence_threshold,
        )
    )


def _resolve_export_path(
    *,
    configured_path: str | None,
    default_output_dir: str | None,
    fallback_name: str,
) -> Path:
    settings = get_settings()
    base_dir = Path(default_output_dir or settings.default_output_dir or settings.exports_dir).expanduser()
    path = Path(configured_path).expanduser() if configured_path else base_dir / fallback_name
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@router.post("/exports/listings", response_model=ExportResponse)
def export_listing_records(session: Session = Depends(get_session)) -> ExportResponse:
    cards = list(session.scalars(select(CardInstance).order_by(CardInstance.internal_sku)).all())
    settings_record = get_or_create_settings(session)
    rows = listing_csv_rows(
        cards,
        default_listing_format=settings_record.default_listing_format,
        confidence_threshold=settings_record.confidence_threshold,
    )
    if settings_record.listing_export_mode == "ebay_direct":
        if not settings_record.ebay_direct_listing_enabled:
            return ExportResponse(
                file_name="cardops-ebay-direct-preview.json",
                content_type="application/json",
                row_count=len(rows),
                path=None,
                delivery_mode="ebay_direct_preview",
                message="Direct eBay mode is selected, but direct listing enable is off. No live requests were sent.",
            )
        if not settings_record.live_ebay_publishing_enabled:
            return ExportResponse(
                file_name="cardops-ebay-direct-preview.json",
                content_type="application/json",
                row_count=len(rows),
                path=None,
                delivery_mode="ebay_direct_preview",
                message="Direct eBay listing is enabled, but live eBay publishing is off. No live requests were sent.",
            )
        if not ebay_token_status(get_settings()).connected:
            raise HTTPException(status_code=409, detail="Connect eBay before direct listing export.")
        missing_policy_fields = [
            label
            for label, value in {
                "merchant location key": settings_record.ebay_merchant_location_key,
                "payment policy ID": settings_record.ebay_payment_policy_id,
                "return policy ID": settings_record.ebay_return_policy_id,
                "fulfillment policy ID": settings_record.ebay_fulfillment_policy_id,
            }.items()
            if not value
        ]
        if missing_policy_fields:
            raise HTTPException(
                status_code=409,
                detail=f"Configure eBay {'/'.join(missing_policy_fields)} before direct listing export.",
            )
        return ExportResponse(
            file_name="cardops-ebay-direct-preview.json",
            content_type="application/json",
            row_count=len(rows),
            path=None,
            delivery_mode="ebay_direct_ready",
            message=(
                "Direct eBay listing is configured and connected. "
                "Live creation is held until listing payload mapping is implemented."
            ),
        )
    path = _resolve_export_path(
        configured_path=settings_record.default_ebay_export_path,
        default_output_dir=settings_record.default_output_dir,
        fallback_name="cardops-ebay-listings.csv",
    )
    path.write_text(render_csv(rows), encoding="utf-8")
    return ExportResponse(
        file_name=path.name,
        content_type="text/csv",
        row_count=len(rows),
        path=str(path),
        delivery_mode="file_upload",
        message="Wrote local eBay listing CSV for manual upload.",
    )


@router.get("/exports/listings.csv")
def download_listing_records(session: Session = Depends(get_session)) -> Response:
    cards = list(session.scalars(select(CardInstance).order_by(CardInstance.internal_sku)).all())
    settings_record = get_or_create_settings(session)
    return Response(
        content=render_csv(
            listing_csv_rows(
                cards,
                default_listing_format=settings_record.default_listing_format,
                confidence_threshold=settings_record.confidence_threshold,
            )
        ),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="cardops-ebay-listings.csv"'},
    )


@router.post("/exports/lots", response_model=ExportResponse)
def export_lot_records(session: Session = Depends(get_session)) -> ExportResponse:
    cards = list(session.scalars(select(CardInstance).order_by(CardInstance.internal_sku)).all())
    settings_record = get_or_create_settings(session)
    rows = []
    for card in cards:
        listing = recommend_listing(
            card,
            default_listing_format=settings_record.default_listing_format,
            confidence_threshold=settings_record.confidence_threshold,
        )
        rows.append(
            {
                "Internal SKU": card.internal_sku,
                "Player": card.player or "",
                "Estimated Value": card.estimated_value or "",
                "Lot Assignment": listing["lot_assignment"],
                "Reason": listing["recommended_listing_format"],
            }
        )
    path = _resolve_export_path(
        configured_path=None,
        default_output_dir=settings_record.default_output_dir,
        fallback_name="cardops-lots.csv",
    )
    path.write_text(render_csv(rows), encoding="utf-8")
    return ExportResponse(file_name=path.name, content_type="text/csv", row_count=len(rows), path=str(path))


@router.post("/exports/file-plan", response_model=ExportResponse)
def export_file_plan(session: Session = Depends(get_session)) -> ExportResponse:
    settings_record = get_or_create_settings(session)
    rows = [
        {
            "Image ID": image.id,
            "Current Path": image.absolute_path,
            "Suggested Action": "none",
            "Reason": "Physical file moves are disabled by default.",
        }
        for image in session.scalars(select(ImageAsset).order_by(ImageAsset.file_name)).all()
    ]
    path = _resolve_export_path(
        configured_path=None,
        default_output_dir=settings_record.default_output_dir,
        fallback_name="cardops-file-plan.csv",
    )
    path.write_text(render_csv(rows), encoding="utf-8")
    return ExportResponse(file_name=path.name, content_type="text/csv", row_count=len(rows), path=str(path))


@router.get("/pricing/{card_id}", response_model=list[PriceSourceClassification])
def pricing_sources(card_id: str, session: Session = Depends(get_session)) -> list[PriceSourceClassification]:
    if session.get(CardInstance, card_id) is None:
        raise HTTPException(status_code=404, detail="Card not found.")
    return [
        PriceSourceClassification(
            source_type="MANUAL_VALUE",
            label="Manual value",
        ),
        PriceSourceClassification(
            source_type="ACTIVE_LISTING",
            label="Active market comparison",
            caution="Active market comparison — not verified sold data.",
        ),
    ]


@router.post("/pricing/search", response_model=list[PriceSourceClassification])
def pricing_search() -> list[PriceSourceClassification]:
    return [
        PriceSourceClassification(
            source_type="ACTIVE_LISTING",
            label="Mock active market comparison",
            caution="Active market comparison — not verified sold data.",
        )
    ]


@router.get("/ebay/status")
def ebay_status() -> dict[str, object]:
    settings = get_settings()
    configured = settings.ebay_client_id_present and settings.ebay_client_secret_present
    oauth = get_ebay_oauth_config(settings)
    token_status = ebay_token_status(settings)
    return {
        "state": "connected" if token_status.connected else "not_connected",
        "environment": settings.ebay_environment,
        "configured": configured,
        "redirect_uri": oauth.redirect_uri,
        "auth_accepted_url": oauth.auth_accepted_url,
        "auth_declined_url": oauth.auth_declined_url,
        "runame_configured": bool(oauth.runame),
        "token": {
            "connected": token_status.connected,
            "has_access_token": token_status.has_access_token,
            "has_refresh_token": token_status.has_refresh_token,
            "access_token_expires_at": token_status.access_token_expires_at,
            "refresh_token_expires_at": token_status.refresh_token_expires_at,
        },
        "limitations": [
            "Read-only seller inventory sync requires successful eBay user authorization.",
            "eBay authorization URLs use EBAY_RUNAME when configured.",
        ],
    }


@router.post("/ebay/connect")
def ebay_connect() -> dict[str, object]:
    try:
        oauth_url = build_configured_authorization_url()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "state": "authorization_url_created",
        **oauth_url,
        "warning": None
        if oauth_url["runame_configured"]
        else "EBAY_RUNAME is not configured; eBay production OAuth usually expects the RuName in redirect_uri.",
    }


@router.post("/ebay/disconnect")
def ebay_disconnect() -> dict[str, object]:
    clear_ebay_token()
    return {"state": "not_connected", "message": "Stored eBay OAuth token was removed."}


def _ebay_authorization_required_response() -> dict[str, object]:
    return {
        "state": "authorization_required",
        "message": "Connect eBay first. Use /ebay/connect, complete consent, then retry sync.",
        "connect": ebay_connect(),
    }


def _ebay_callback_browser_response(payload: dict[str, object]) -> HTMLResponse:
    status = str(payload.get("status") or "received")
    exchange = payload.get("exchange") if isinstance(payload.get("exchange"), dict) else {}
    exchange_error = ""
    if isinstance(exchange, dict):
        exchange_error = str(exchange.get("error") or "")
    connected = status == "connected"
    declined = status == "declined"
    title = "eBay connected" if connected else "eBay connection not completed"
    message = str(payload.get("message") or "")
    detail = str(payload.get("error") or exchange_error or "")
    body_class = "ok" if connected else "warn" if declined or detail else "warn"
    escaped_title = html.escape(title)
    escaped_message = html.escape(message)
    escaped_detail = html.escape(detail)
    app_url = "http://127.0.0.1:5173"
    redirect_script = (
        f"<script>window.setTimeout(function () {{ window.location.href = '{app_url}'; }}, 2500);</script>"
        if connected
        else ""
    )
    detail_html = f"<p><strong>Detail:</strong> {escaped_detail}</p>" if escaped_detail else ""
    close_text = (
        "CardOps will refresh its eBay status shortly."
        if connected
        else "Keep this page open and use the detail above to fix the OAuth exchange."
    )
    content = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CardOps AI eBay Callback</title>
    <style>
      :root {{
        color: #17202a;
        background: #f7f9fb;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 24px;
      }}
      main {{
        width: min(760px, 100%);
        background: #ffffff;
        border: 1px solid #dce3ea;
        border-radius: 8px;
        padding: 24px;
      }}
      h1 {{ margin: 0 0 8px; font-size: 24px; }}
      p {{ color: #526173; line-height: 1.55; }}
      .status {{
        border-radius: 6px;
        border: 1px solid #dce3ea;
        background: #f8fafc;
        padding: 12px;
        margin-top: 16px;
      }}
      .ok {{ border-color: #99d8c8; background: #ecfdf7; }}
      .warn {{ border-color: #f3cd78; background: #fff8e5; }}
      a {{
        display: inline-flex;
        align-items: center;
        min-height: 36px;
        padding: 0 12px;
        border-radius: 6px;
        border: 1px solid #0f766e;
        background: #0f766e;
        color: #ffffff;
        text-decoration: none;
        font-weight: 700;
        margin-top: 12px;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>{escaped_title}</h1>
      <div class="status {body_class}">
        <p>{escaped_message}</p>
        {detail_html}
        <p>{html.escape(close_text)}</p>
      </div>
      <a href="{app_url}">Open CardOps</a>
    </main>
    {redirect_script}
  </body>
</html>"""
    return HTMLResponse(content)


@router.post("/ebay/sync")
@router.get("/ebay/listings")
def ebay_read_only_sync(
    limit: int | None = None,
    offset: int | None = None,
    include_offers: bool | None = None,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    settings_record = get_or_create_settings(session)
    effective_limit = min(max(limit if limit is not None else settings_record.ebay_sync_limit, 1), 200)
    effective_offset = max(offset if offset is not None else settings_record.ebay_sync_offset, 0)
    effective_include_offers = (
        include_offers if include_offers is not None else settings_record.ebay_sync_include_offers
    )
    try:
        inventory = get_inventory_items(limit=effective_limit, offset=effective_offset)
        offers = (
            get_offers_for_inventory_items(inventory, limit=effective_limit)
            if effective_include_offers
            else None
        )
    except EbayAuthorizationRequired:
        return _ebay_authorization_required_response()
    except EbayApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "state": "synced",
        "provider": "EbayInventoryApi",
        "environment": get_settings().ebay_environment,
        "sync_config": {
            "limit": effective_limit,
            "offset": effective_offset,
            "include_offers": effective_include_offers,
        },
        "inventory": inventory,
        "offers": offers,
        "read_only": True,
    }


@router.get("/ebay/callback", response_model=None)
def ebay_callback(
    code: str | None = None,
    state: str | None = None,
    expires_in: int | None = None,
    error: str | None = None,
    error_description: str | None = None,
    browser: bool = False,
    session: Session = Depends(get_session),
) -> dict[str, object] | HTMLResponse:
    code_details = redact_oauth_code(code)
    if error:
        details = {
            "error": error,
            "error_description": error_description,
            "state": state,
            "code": code_details,
        }
        from cardops_api.audit import add_audit_log

        add_audit_log(session, "ebay.oauth_declined", entity_type="ebay_oauth", details=details)
        session.commit()
        payload: dict[str, object] = {
            "status": "declined",
            "message": "eBay authorization was declined or failed.",
            "error": error,
            "state": state,
        }
        if browser:
            return _ebay_callback_browser_response(payload)
        return payload

    if not code:
        raise HTTPException(status_code=400, detail="Missing eBay OAuth code.")

    from cardops_api.audit import add_audit_log

    exchange_result: dict[str, object] | None = None
    exchange_error: str | None = None
    try:
        exchange_result = exchange_authorization_code(code)
    except EbayAuthorizationRequired as exc:
        exchange_error = str(exc)
    except EbayApiError as exc:
        exchange_error = str(exc)

    add_audit_log(
        session,
        "ebay.oauth_code_received",
        entity_type="ebay_oauth",
        details={
            "state": state,
            "expires_in": expires_in,
            "code": code_details,
            "exchange_succeeded": exchange_result is not None,
            "exchange_error": exchange_error,
        },
    )
    session.commit()
    payload = {
        "status": "connected" if exchange_result else "received",
        "message": "eBay OAuth code received and token exchange completed."
        if exchange_result
        else "eBay OAuth code received, but token exchange did not complete.",
        "state": state,
        "expires_in": expires_in,
        "code": code_details,
        "exchange": exchange_result
        or {
            "connected": False,
            "error": exchange_error,
        },
    }
    if browser:
        return _ebay_callback_browser_response(payload)
    return payload


@router.post("/ebay/import-url")
def ebay_import_url(payload: dict[str, str]) -> dict[str, object]:
    raw = payload.get("value") or payload.get("url") or payload.get("item_number") or ""
    digits = "".join(ch for ch in raw if ch.isdigit())
    item_number = digits[-12:] if digits else raw.strip()
    if not item_number:
        raise HTTPException(status_code=400, detail="Provide an eBay URL or item number.")
    return {
        "provider": "MockEbayProvider",
        "item_number": item_number,
        "ownership": "unknown_public_comparison",
        "snapshot": {
            "title": "Mock imported listing snapshot",
            "price_source": "ACTIVE_LISTING",
            "price_caution": "Active market comparison — not verified sold data.",
        },
    }


@router.get("/listings")
@router.get("/listings/{listing_id}")
@router.post("/listings/{listing_id}/audit")
@router.post("/listings/bulk-audit")
@router.post("/lots/recommend")
@router.get("/lots")
@router.post("/lots")
@router.patch("/lots/{lot_id}")
@router.post("/lots/{lot_id}/lock")
@router.get("/drafts")
@router.post("/drafts")
@router.post("/drafts/{draft_id}/validate")
@router.post("/drafts/{draft_id}/approve")
@router.post("/drafts/{draft_id}/publish")
def planned_modules(
    listing_id: str | None = None,
    lot_id: str | None = None,
    draft_id: str | None = None,
) -> dict[str, object]:
    return {
        "status": "planned",
        "message": "This module is documented and will be implemented in a later phase.",
        "id": listing_id or lot_id or draft_id,
    }
