from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    database: str
    demo_mode: bool
    version: str


class ProviderCapabilityResponse(BaseModel):
    name: str
    status: str
    capabilities: list[str]
    limitations: list[str]


class SystemCapabilitiesResponse(BaseModel):
    demo_mode: bool
    local_only_mode: bool
    cloud_ai_enabled: bool
    live_ebay_publishing_enabled: bool
    physical_file_moves_enabled: bool
    listing_export_mode: str
    ebay_direct_listing_enabled: bool
    ebay_sync_limit: int
    ebay_sync_offset: int
    ebay_sync_include_offers: bool
    default_listing_format: str
    confidence_threshold: float
    providers: list[ProviderCapabilityResponse]


class SettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    demo_mode: bool
    local_only_mode: bool
    cloud_ai_enabled: bool
    live_ebay_publishing_enabled: bool
    physical_file_moves_enabled: bool
    listing_export_mode: Literal["file_upload", "ebay_direct"]
    ebay_direct_listing_enabled: bool
    ebay_marketplace_id: str
    ebay_merchant_location_key: str | None
    ebay_payment_policy_id: str | None
    ebay_return_policy_id: str | None
    ebay_fulfillment_policy_id: str | None
    ebay_sync_limit: int
    ebay_sync_offset: int
    ebay_sync_include_offers: bool
    default_listing_format: Literal["fixed_price", "auction", "auction_or_lot"]
    confidence_threshold: float
    tesseract_cmd: str | None
    ocr_language: str
    default_input_dir: str | None
    default_output_dir: str | None
    default_inventory_path: str | None
    default_ebay_export_path: str | None
    daily_ai_request_limit: int
    daily_ai_cost_limit: float
    updated_at: datetime


class SettingsUpdate(BaseModel):
    demo_mode: bool | None = None
    local_only_mode: bool | None = None
    cloud_ai_enabled: bool | None = None
    live_ebay_publishing_enabled: bool | None = None
    physical_file_moves_enabled: bool | None = None
    listing_export_mode: Literal["file_upload", "ebay_direct"] | None = None
    ebay_direct_listing_enabled: bool | None = None
    ebay_marketplace_id: str | None = Field(default=None, min_length=3, max_length=40)
    ebay_merchant_location_key: str | None = Field(default=None, max_length=120)
    ebay_payment_policy_id: str | None = Field(default=None, max_length=120)
    ebay_return_policy_id: str | None = Field(default=None, max_length=120)
    ebay_fulfillment_policy_id: str | None = Field(default=None, max_length=120)
    ebay_sync_limit: int | None = Field(default=None, ge=1, le=200)
    ebay_sync_offset: int | None = Field(default=None, ge=0)
    ebay_sync_include_offers: bool | None = None
    default_listing_format: Literal["fixed_price", "auction", "auction_or_lot"] | None = None
    confidence_threshold: float | None = Field(default=None, ge=0, le=1)
    tesseract_cmd: str | None = Field(default=None, max_length=1024)
    ocr_language: str | None = Field(default=None, min_length=1, max_length=40)
    default_input_dir: str | None = Field(default=None, max_length=1024)
    default_output_dir: str | None = Field(default=None, max_length=1024)
    default_inventory_path: str | None = Field(default=None, max_length=1024)
    default_ebay_export_path: str | None = Field(default=None, max_length=1024)
    daily_ai_request_limit: int | None = Field(default=None, ge=0)
    daily_ai_cost_limit: float | None = Field(default=None, ge=0)


class DirectorySelectRequest(BaseModel):
    path: str
    label: str | None = None
    recursive: bool = True
    exclude_patterns: list[str] = Field(default_factory=list)
    allow_symlinks: bool = False


class DirectoryUpdateRequest(BaseModel):
    path: str | None = None
    label: str | None = Field(default=None, max_length=200)
    recursive: bool | None = None
    exclude_patterns: list[str] | None = None
    allow_symlinks: bool | None = None


class DirectoryRemoveRequest(BaseModel):
    remove_index_records: bool = False
    confirmed: bool = False


class DirectoryBrowseResponse(BaseModel):
    path: str | None


class DirectoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    path: str
    normalized_path_key: str | None = None
    label: str | None
    recursive: bool
    exclude_patterns: list[str]
    allow_symlinks: bool
    created_at: datetime
    revoked_at: datetime | None
    status: str = "unknown"
    status_detail: str = ""
    image_count: int = 0
    pending_identification_count: int = 0


class ScanDirectoryRequest(BaseModel):
    directory_id: str
    run_inline: bool = False


class ImageAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    directory_id: str
    absolute_path: str
    relative_path: str
    file_name: str
    extension: str
    file_size: int
    created_time: datetime | None
    modified_time: datetime | None
    sha256: str | None
    perceptual_hash: str | None
    width: int | None
    height: int | None
    thumbnail_path: str | None
    imported_at: datetime
    processing_status: str
    duplicate_status: str
    front_back_assignment: str | None
    original_location: str
    card_instance_id: str | None
    error_message: str | None


class CardCreate(BaseModel):
    sport: str | None = None
    player: str | None = None
    team: str | None = None
    manufacturer: str | None = None
    brand: str | None = None
    set_name: str | None = None
    set_year: int | None = Field(default=None, ge=1800, le=2200)
    card_number: str | None = None
    subset: str | None = None
    variation: str | None = None
    parallel: str | None = None
    rookie: bool = False
    autograph: bool = False
    relic: bool = False
    serial_number_current: int | None = Field(default=None, ge=0)
    serial_number_total: int | None = Field(default=None, ge=0)
    raw_or_graded: str = "raw"
    grading_company: str | None = None
    grade: str | None = None
    quantity: int = Field(default=1, ge=1)
    condition_notes: str | None = None
    acquisition_cost: float | None = Field(default=None, ge=0)
    estimated_value: float | None = Field(default=None, ge=0)
    storage_location: str | None = None
    processing_status: str = "manual"
    confidence: float | None = Field(default=None, ge=0, le=1)
    tags: list[str] = Field(default_factory=list)


class CardUpdate(CardCreate):
    rookie: bool | None = None
    autograph: bool | None = None
    relic: bool | None = None
    raw_or_graded: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    processing_status: str | None = None
    tags: list[str] | None = None


class CardResponse(CardCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    internal_sku: str
    created_at: datetime
    updated_at: datetime


class ProvenanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_type: str
    entity_id: str
    field_name: str
    value: str | None
    normalized_value: str | None
    source_type: str
    source_identifier: str | None
    confidence: float | None
    created_at: datetime
    model_or_engine: str | None
    schema_version: str
    prompt_version: str | None
    user_override: bool


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    status: str
    payload: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    attempts: int
    max_attempts: int
    cancellation_requested: bool
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class BulkUpdateRequest(BaseModel):
    card_ids: list[str]
    patch: CardUpdate


class PairRequest(BaseModel):
    image_ids: list[str] | None = None


class PairCandidate(BaseModel):
    front_image_id: str
    back_image_id: str
    confidence: float
    reason: str


class ExportResponse(BaseModel):
    file_name: str
    content_type: str
    row_count: int
    path: str | None = None
    delivery_mode: str = "file_upload"
    message: str | None = None


class PriceSourceClassification(BaseModel):
    source_type: Literal[
        "VERIFIED_OWN_SALE",
        "AUTHORIZED_SOLD_COMP",
        "USER_IMPORTED_SOLD_COMP",
        "ACTIVE_LISTING",
        "CATALOG_ESTIMATE",
        "AI_ESTIMATE",
        "MANUAL_VALUE",
    ]
    label: str
    caution: str | None = None


class DependencyStatusResponse(BaseModel):
    name: str
    status: str
    detail: str
    path: str | None = None
    version: str | None = None


class OcrResultResponse(BaseModel):
    status: str
    engine: str
    text: str
    confidence: float
    lines: list[str] = Field(default_factory=list)
    error: str | None = None


class FieldEvidenceResponse(BaseModel):
    field_name: str
    value: str
    source_type: str
    source_identifier: str
    confidence: float


class CardIdentificationResponse(BaseModel):
    image_id: str
    source_image: str
    ocr: OcrResultResponse
    candidate: dict[str, Any]
    confidence: float
    unresolved_fields: list[str]
    evidence: list[FieldEvidenceResponse]
    normalized_text: str


class CardFromImageRequest(BaseModel):
    overrides: CardUpdate | None = None


class ListingRecommendationResponse(BaseModel):
    title: str
    length: int
    limit: int
    warnings: list[str]
    recommended_listing_format: str
    recommended_price: float | None
    pricing_source: str
    pricing_configured: bool
    price_caution: str | None
    lot_assignment: str
    data_source: str
