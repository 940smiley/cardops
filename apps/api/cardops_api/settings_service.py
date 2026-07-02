from __future__ import annotations

from sqlalchemy.orm import Session

from cardops_api.config import AppSettings, get_settings
from cardops_api.models import SettingsRecord, utc_now


def _clean_optional(value: str) -> str | None:
    cleaned = value.strip()
    return cleaned or None


def _default_output_dir(app_settings: AppSettings) -> str:
    return app_settings.default_output_dir or str(app_settings.exports_dir)


def _default_inventory_path(app_settings: AppSettings) -> str:
    return app_settings.default_inventory_path or str(app_settings.exports_dir / "cardops-inventory.csv")


def _default_ebay_export_path(app_settings: AppSettings) -> str:
    return app_settings.default_ebay_export_path or str(app_settings.exports_dir / "cardops-ebay-listings.csv")


def _apply_missing_defaults(record: SettingsRecord, app_settings: AppSettings) -> bool:
    changed = False
    missing_defaults: dict[str, object] = {
        "tesseract_cmd": app_settings.tesseract_cmd,
        "ocr_language": app_settings.ocr_language,
        "default_input_dir": app_settings.default_input_dir,
        "default_output_dir": _default_output_dir(app_settings),
        "default_inventory_path": _default_inventory_path(app_settings),
        "default_ebay_export_path": _default_ebay_export_path(app_settings),
    }
    for field_name, default_value in missing_defaults.items():
        if default_value and not getattr(record, field_name):
            setattr(record, field_name, default_value)
            changed = True
    if record.ebay_sync_limit < 1:
        record.ebay_sync_limit = app_settings.ebay_sync_limit
        changed = True
    if record.default_listing_format not in {"fixed_price", "auction", "auction_or_lot"}:
        record.default_listing_format = app_settings.default_listing_format
        changed = True
    return changed


def get_or_create_settings(session: Session) -> SettingsRecord:
    record = session.get(SettingsRecord, 1)
    if record is not None:
        app_settings = get_settings()
        if _apply_missing_defaults(record, app_settings):
            record.updated_at = utc_now()
            session.add(record)
            session.commit()
            session.refresh(record)
        return record
    app_settings = get_settings()
    record = SettingsRecord(
        id=1,
        demo_mode=app_settings.demo_mode,
        local_only_mode=app_settings.local_only_mode,
        cloud_ai_enabled=app_settings.cloud_ai_enabled,
        live_ebay_publishing_enabled=app_settings.live_ebay_publishing_enabled,
        physical_file_moves_enabled=app_settings.physical_file_moves_enabled,
        listing_export_mode=app_settings.listing_export_mode,
        ebay_direct_listing_enabled=app_settings.ebay_direct_listing_enabled,
        ebay_marketplace_id=app_settings.ebay_marketplace_id,
        ebay_merchant_location_key=app_settings.ebay_merchant_location_key,
        ebay_payment_policy_id=app_settings.ebay_payment_policy_id,
        ebay_return_policy_id=app_settings.ebay_return_policy_id,
        ebay_fulfillment_policy_id=app_settings.ebay_fulfillment_policy_id,
        ebay_sync_limit=app_settings.ebay_sync_limit,
        ebay_sync_offset=app_settings.ebay_sync_offset,
        ebay_sync_include_offers=app_settings.ebay_sync_include_offers,
        default_listing_format=app_settings.default_listing_format,
        confidence_threshold=app_settings.confidence_threshold,
        tesseract_cmd=app_settings.tesseract_cmd,
        ocr_language=app_settings.ocr_language,
        default_input_dir=app_settings.default_input_dir,
        default_output_dir=_default_output_dir(app_settings),
        default_inventory_path=_default_inventory_path(app_settings),
        default_ebay_export_path=_default_ebay_export_path(app_settings),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def update_settings(
    session: Session,
    *,
    demo_mode: bool | None = None,
    local_only_mode: bool | None = None,
    cloud_ai_enabled: bool | None = None,
    live_ebay_publishing_enabled: bool | None = None,
    physical_file_moves_enabled: bool | None = None,
    listing_export_mode: str | None = None,
    ebay_direct_listing_enabled: bool | None = None,
    ebay_marketplace_id: str | None = None,
    ebay_merchant_location_key: str | None = None,
    ebay_payment_policy_id: str | None = None,
    ebay_return_policy_id: str | None = None,
    ebay_fulfillment_policy_id: str | None = None,
    ebay_sync_limit: int | None = None,
    ebay_sync_offset: int | None = None,
    ebay_sync_include_offers: bool | None = None,
    default_listing_format: str | None = None,
    confidence_threshold: float | None = None,
    tesseract_cmd: str | None = None,
    ocr_language: str | None = None,
    default_input_dir: str | None = None,
    default_output_dir: str | None = None,
    default_inventory_path: str | None = None,
    default_ebay_export_path: str | None = None,
    daily_ai_request_limit: int | None = None,
    daily_ai_cost_limit: float | None = None,
) -> SettingsRecord:
    record = get_or_create_settings(session)
    if demo_mode is not None:
        record.demo_mode = demo_mode
    if local_only_mode is not None:
        record.local_only_mode = local_only_mode
    if cloud_ai_enabled is not None:
        record.cloud_ai_enabled = cloud_ai_enabled
    if live_ebay_publishing_enabled is not None:
        record.live_ebay_publishing_enabled = live_ebay_publishing_enabled
    if physical_file_moves_enabled is not None:
        record.physical_file_moves_enabled = physical_file_moves_enabled
    if listing_export_mode is not None:
        record.listing_export_mode = listing_export_mode
    if ebay_direct_listing_enabled is not None:
        record.ebay_direct_listing_enabled = ebay_direct_listing_enabled
    if ebay_marketplace_id is not None:
        record.ebay_marketplace_id = ebay_marketplace_id.strip() or "EBAY_US"
    if ebay_merchant_location_key is not None:
        record.ebay_merchant_location_key = _clean_optional(ebay_merchant_location_key)
    if ebay_payment_policy_id is not None:
        record.ebay_payment_policy_id = _clean_optional(ebay_payment_policy_id)
    if ebay_return_policy_id is not None:
        record.ebay_return_policy_id = _clean_optional(ebay_return_policy_id)
    if ebay_fulfillment_policy_id is not None:
        record.ebay_fulfillment_policy_id = _clean_optional(ebay_fulfillment_policy_id)
    if ebay_sync_limit is not None:
        record.ebay_sync_limit = ebay_sync_limit
    if ebay_sync_offset is not None:
        record.ebay_sync_offset = ebay_sync_offset
    if ebay_sync_include_offers is not None:
        record.ebay_sync_include_offers = ebay_sync_include_offers
    if default_listing_format is not None:
        record.default_listing_format = default_listing_format
    if confidence_threshold is not None:
        record.confidence_threshold = confidence_threshold
    if tesseract_cmd is not None:
        record.tesseract_cmd = _clean_optional(tesseract_cmd)
    if ocr_language is not None:
        record.ocr_language = ocr_language.strip() or "eng"
    if default_input_dir is not None:
        record.default_input_dir = _clean_optional(default_input_dir)
    if default_output_dir is not None:
        record.default_output_dir = _clean_optional(default_output_dir)
    if default_inventory_path is not None:
        record.default_inventory_path = _clean_optional(default_inventory_path)
    if default_ebay_export_path is not None:
        record.default_ebay_export_path = _clean_optional(default_ebay_export_path)
    if daily_ai_request_limit is not None:
        record.daily_ai_request_limit = daily_ai_request_limit
    if daily_ai_cost_limit is not None:
        record.daily_ai_cost_limit = daily_ai_cost_limit
    record.updated_at = utc_now()
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
