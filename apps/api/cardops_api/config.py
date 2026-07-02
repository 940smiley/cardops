from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_EBAY_CALLBACK_URL = "https://940smiley.github.io/cardops/ebay/callback/"
DEFAULT_WINDOWS_TESSERACT_CMD = Path("E:/Apps/tesseract-ocr/tesseract.exe")


def _load_env_file() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        env_path = ROOT_DIR / ".ENV"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


def _as_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(name: str, default: int, *, minimum: int = 0, maximum: int | None = None) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


@dataclass(frozen=True)
class AppSettings:
    env: str
    database_url: str
    api_host: str
    api_port: int
    demo_mode: bool
    log_level: str
    local_only_mode: bool
    cloud_ai_enabled: bool
    live_ebay_publishing_enabled: bool
    physical_file_moves_enabled: bool
    listing_export_mode: str
    ebay_direct_listing_enabled: bool
    ebay_marketplace_id: str
    ebay_merchant_location_key: str | None
    ebay_payment_policy_id: str | None
    ebay_return_policy_id: str | None
    ebay_fulfillment_policy_id: str | None
    ebay_sync_limit: int
    ebay_sync_offset: int
    ebay_sync_include_offers: bool
    openai_api_key_present: bool
    openai_model_fast: str
    openai_model_accurate: str
    ebay_environment: str
    ebay_client_id_present: bool
    ebay_client_secret_present: bool
    ebay_client_id: str | None
    ebay_client_secret: str | None
    ebay_redirect_uri: str
    ebay_runame: str | None
    ebay_scopes: str
    ebay_auth_accepted_url: str | None
    ebay_auth_declined_url: str | None
    tesseract_cmd: str | None
    ocr_language: str
    default_input_dir: str | None
    default_output_dir: str | None
    default_inventory_path: str | None
    default_ebay_export_path: str | None
    confidence_threshold: float
    default_listing_format: str
    data_dir: Path
    thumbnail_dir: Path
    demo_dir: Path
    exports_dir: Path


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    _load_env_file()
    data_dir = Path(os.getenv("CARDOPS_DATA_DIR", str(ROOT_DIR / "data"))).expanduser()
    return AppSettings(
        env=os.getenv("CARDOPS_ENV", "development"),
        database_url=os.getenv("CARDOPS_DATABASE_URL", "sqlite:///./data/cardops.db"),
        api_host=os.getenv("CARDOPS_API_HOST", "127.0.0.1"),
        api_port=int(os.getenv("CARDOPS_API_PORT", "8000")),
        demo_mode=_as_bool("CARDOPS_DEMO_MODE", True),
        log_level=os.getenv("CARDOPS_LOG_LEVEL", "INFO"),
        local_only_mode=_as_bool("CARDOPS_LOCAL_ONLY_MODE", True),
        cloud_ai_enabled=_as_bool("CARDOPS_CLOUD_AI_ENABLED", False),
        live_ebay_publishing_enabled=_as_bool("CARDOPS_LIVE_EBAY_PUBLISHING_ENABLED", False),
        physical_file_moves_enabled=_as_bool("CARDOPS_PHYSICAL_FILE_MOVES_ENABLED", False),
        listing_export_mode=os.getenv("CARDOPS_LISTING_EXPORT_MODE", "file_upload"),
        ebay_direct_listing_enabled=_as_bool("CARDOPS_EBAY_DIRECT_LISTING_ENABLED", False),
        ebay_marketplace_id=os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US"),
        ebay_merchant_location_key=os.getenv("EBAY_MERCHANT_LOCATION_KEY") or None,
        ebay_payment_policy_id=os.getenv("EBAY_PAYMENT_POLICY_ID") or None,
        ebay_return_policy_id=os.getenv("EBAY_RETURN_POLICY_ID") or None,
        ebay_fulfillment_policy_id=os.getenv("EBAY_FULFILLMENT_POLICY_ID") or None,
        ebay_sync_limit=_as_int("CARDOPS_EBAY_SYNC_LIMIT", 25, minimum=1, maximum=200),
        ebay_sync_offset=_as_int("CARDOPS_EBAY_SYNC_OFFSET", 0),
        ebay_sync_include_offers=_as_bool("CARDOPS_EBAY_SYNC_INCLUDE_OFFERS", True),
        openai_api_key_present=bool(os.getenv("OPENAI_API_KEY")),
        openai_model_fast=os.getenv("OPENAI_MODEL_FAST", "gpt-4.1-mini"),
        openai_model_accurate=os.getenv("OPENAI_MODEL_ACCURATE", "gpt-4.1"),
        ebay_environment=os.getenv("EBAY_ENVIRONMENT", "sandbox"),
        ebay_client_id_present=bool(os.getenv("EBAY_CLIENT_ID")),
        ebay_client_secret_present=bool(os.getenv("EBAY_CLIENT_SECRET")),
        ebay_client_id=os.getenv("EBAY_CLIENT_ID") or None,
        ebay_client_secret=os.getenv("EBAY_CLIENT_SECRET") or None,
        ebay_redirect_uri=os.getenv(
            "EBAY_REDIRECT_URI",
            DEFAULT_EBAY_CALLBACK_URL,
        ),
        ebay_runame=os.getenv("EBAY_RUNAME") or None,
        ebay_scopes=os.getenv(
            "EBAY_SCOPES",
            "https://api.ebay.com/oauth/api_scope "
            "https://api.ebay.com/oauth/api_scope/sell.inventory",
        ),
        ebay_auth_accepted_url=os.getenv("EBAY_AUTH_ACCEPTED_URL") or None,
        ebay_auth_declined_url=os.getenv("EBAY_AUTH_DECLINED_URL") or None,
        tesseract_cmd=os.getenv("CARDOPS_TESSERACT_CMD")
        or (str(DEFAULT_WINDOWS_TESSERACT_CMD) if DEFAULT_WINDOWS_TESSERACT_CMD.exists() else None),
        ocr_language=os.getenv("CARDOPS_OCR_LANGUAGE", "eng"),
        default_input_dir=os.getenv("CARDOPS_DEFAULT_INPUT_DIR") or None,
        default_output_dir=os.getenv("CARDOPS_DEFAULT_OUTPUT_DIR") or None,
        default_inventory_path=os.getenv("CARDOPS_INVENTORY_PATH") or None,
        default_ebay_export_path=os.getenv("CARDOPS_EBAY_EXPORT_PATH") or None,
        confidence_threshold=float(os.getenv("CARDOPS_CONFIDENCE_THRESHOLD", "0.72")),
        default_listing_format=os.getenv("CARDOPS_DEFAULT_LISTING_FORMAT", "fixed_price"),
        data_dir=data_dir,
        thumbnail_dir=data_dir / "thumbnails",
        demo_dir=data_dir / "demo",
        exports_dir=data_dir / "exports",
    )


def clear_settings_cache() -> None:
    get_settings.cache_clear()
