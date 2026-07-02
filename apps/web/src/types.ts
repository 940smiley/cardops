export interface HealthResponse {
  status: string;
  database: string;
  demo_mode: boolean;
  version: string;
}

export interface ProviderCapability {
  name: string;
  status: string;
  capabilities: string[];
  limitations: string[];
}

export interface SystemCapabilities {
  demo_mode: boolean;
  local_only_mode: boolean;
  cloud_ai_enabled: boolean;
  live_ebay_publishing_enabled: boolean;
  physical_file_moves_enabled: boolean;
  listing_export_mode: "file_upload" | "ebay_direct";
  ebay_direct_listing_enabled: boolean;
  ebay_sync_limit: number;
  ebay_sync_offset: number;
  ebay_sync_include_offers: boolean;
  default_listing_format: "fixed_price" | "auction" | "auction_or_lot";
  confidence_threshold: number;
  providers: ProviderCapability[];
}

export interface SettingsRecord {
  demo_mode: boolean;
  local_only_mode: boolean;
  cloud_ai_enabled: boolean;
  live_ebay_publishing_enabled: boolean;
  physical_file_moves_enabled: boolean;
  listing_export_mode: "file_upload" | "ebay_direct";
  ebay_direct_listing_enabled: boolean;
  ebay_marketplace_id: string;
  ebay_merchant_location_key: string | null;
  ebay_payment_policy_id: string | null;
  ebay_return_policy_id: string | null;
  ebay_fulfillment_policy_id: string | null;
  ebay_sync_limit: number;
  ebay_sync_offset: number;
  ebay_sync_include_offers: boolean;
  default_listing_format: "fixed_price" | "auction" | "auction_or_lot";
  confidence_threshold: number;
  tesseract_cmd: string | null;
  ocr_language: string;
  default_input_dir: string | null;
  default_output_dir: string | null;
  default_inventory_path: string | null;
  default_ebay_export_path: string | null;
  daily_ai_request_limit: number;
  daily_ai_cost_limit: number;
  updated_at: string;
}

export interface DirectoryRoot {
  id: string;
  path: string;
  normalized_path_key: string | null;
  label: string | null;
  recursive: boolean;
  exclude_patterns: string[];
  allow_symlinks: boolean;
  created_at: string;
  revoked_at: string | null;
  status: "active" | "revoked" | "missing" | "invalid" | "unavailable" | "moved" | "unknown";
  status_detail: string;
  image_count: number;
  pending_identification_count: number;
}

export interface ImageAsset {
  id: string;
  directory_id: string;
  absolute_path: string;
  relative_path: string;
  file_name: string;
  extension: string;
  file_size: number;
  created_time: string | null;
  modified_time: string | null;
  sha256: string | null;
  perceptual_hash: string | null;
  width: number | null;
  height: number | null;
  thumbnail_path: string | null;
  imported_at: string;
  processing_status: string;
  duplicate_status: string;
  front_back_assignment: string | null;
  original_location: string;
  card_instance_id: string | null;
  error_message: string | null;
}

export interface CardInstance {
  id: string;
  internal_sku: string;
  sport: string | null;
  player: string | null;
  team: string | null;
  manufacturer: string | null;
  brand: string | null;
  set_name: string | null;
  set_year: number | null;
  card_number: string | null;
  subset: string | null;
  variation: string | null;
  parallel: string | null;
  rookie: boolean;
  autograph: boolean;
  relic: boolean;
  serial_number_current: number | null;
  serial_number_total: number | null;
  raw_or_graded: string;
  grading_company: string | null;
  grade: string | null;
  quantity: number;
  condition_notes: string | null;
  acquisition_cost: number | null;
  estimated_value: number | null;
  storage_location: string | null;
  processing_status: string;
  confidence: number | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface JobRecord {
  id: string;
  type: string;
  status: string;
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
  attempts: number;
  max_attempts: number;
  cancellation_requested: boolean;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface OcrResult {
  status: string;
  engine: string;
  text: string;
  confidence: number;
  lines: string[];
  error: string | null;
}

export interface FieldEvidence {
  field_name: string;
  value: string;
  source_type: string;
  source_identifier: string;
  confidence: number;
}

export interface CardIdentification {
  image_id: string;
  source_image: string;
  ocr: OcrResult;
  candidate: Partial<CardInstance>;
  confidence: number;
  unresolved_fields: string[];
  evidence: FieldEvidence[];
  normalized_text: string;
}

export interface ExportResult {
  file_name: string;
  content_type: string;
  row_count: number;
  path: string | null;
  delivery_mode: string;
  message: string | null;
}

export interface EbayTokenSummary {
  connected: boolean;
  has_access_token: boolean;
  has_refresh_token: boolean;
  access_token_expires_at: string | null;
  refresh_token_expires_at: string | null;
}

export interface EbayStatus {
  state: string;
  environment: string;
  configured: boolean;
  redirect_uri: string;
  auth_accepted_url: string;
  auth_declined_url: string;
  runame_configured: boolean;
  token: EbayTokenSummary;
  limitations: string[];
}

export interface EbayConnectResponse {
  state: string;
  authorization_url: string;
  redirect_uri: string;
  auth_accepted_url: string;
  auth_declined_url: string;
  runame_configured: boolean;
  warning: string | null;
}

export interface EbayListingSyncResponse {
  state: string;
  message?: string;
  provider?: string;
  environment?: string;
  read_only?: boolean;
  inventory?: {
    total?: number;
    size?: number;
    href?: string;
    limit?: number;
    offset?: number;
    inventoryItems?: unknown[];
  };
  offers?: {
    total?: number;
    size?: number;
    href?: string;
    limit?: number;
    offset?: number;
    offers?: unknown[];
    errors?: { sku?: string; error: string }[];
    inventoryOnlySkus?: string[];
    message?: string | null;
  } | null;
  sync_config?: {
    limit: number;
    offset: number;
    include_offers: boolean;
  };
  connect?: EbayConnectResponse;
}
