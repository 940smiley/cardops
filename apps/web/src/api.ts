import type {
  CardInstance,
  CardIdentification,
  DirectoryRoot,
  ExportResult,
  EbayConnectResponse,
  EbayListingSyncResponse,
  EbayStatus,
  HealthResponse,
  ImageAsset,
  JobRecord,
  SettingsRecord,
  SystemCapabilities
} from "./types";

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

type EbaySyncParams = {
  limit?: number;
  offset?: number;
  include_offers?: boolean;
};

function ebaySyncPath(path: string, params?: EbaySyncParams): string {
  const search = new URLSearchParams();
  if (params?.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  if (params?.offset !== undefined) {
    search.set("offset", String(params.offset));
  }
  if (params?.include_offers !== undefined) {
    search.set("include_offers", String(params.include_offers));
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  capabilities: () => request<SystemCapabilities>("/system/capabilities"),
  settings: () => request<SettingsRecord>("/settings"),
  updateSettings: (payload: Partial<SettingsRecord>) =>
    request<SettingsRecord>("/settings", { method: "PUT", body: JSON.stringify(payload) }),
  directories: () => request<DirectoryRoot[]>("/directories"),
  browseDirectory: () => request<{ path: string | null }>("/directories/browse", { method: "POST" }),
  selectDirectory: (payload: {
    path: string;
    label?: string;
    recursive: boolean;
    exclude_patterns: string[];
    allow_symlinks: boolean;
  }) => request<DirectoryRoot>("/directories/select", { method: "POST", body: JSON.stringify(payload) }),
  updateDirectory: (
    directoryId: string,
    payload: Partial<Pick<DirectoryRoot, "path" | "label" | "recursive" | "exclude_patterns" | "allow_symlinks">>
  ) => request<DirectoryRoot>(`/directories/${directoryId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  reconnectDirectory: (directoryId: string) =>
    request<DirectoryRoot>(`/directories/${directoryId}/reconnect`, { method: "POST" }),
  openDirectory: (directoryId: string) =>
    request<{ status: string; path: string }>(`/directories/${directoryId}/open`, { method: "POST" }),
  removeDirectory: (directoryId: string, payload: { confirmed: boolean; remove_index_records: boolean }) =>
    request<DirectoryRoot>(`/directories/${directoryId}`, { method: "DELETE", body: JSON.stringify(payload) }),
  scanDirectory: (directoryId: string) =>
    request<JobRecord>("/directories/scan", {
      method: "POST",
      body: JSON.stringify({ directory_id: directoryId, run_inline: false })
    }),
  images: () => request<ImageAsset[]>("/images"),
  thumbnailUrl: (imageId: string) => `${API_BASE}/images/${imageId}/thumbnail`,
  identifyImage: (imageId: string) =>
    request<CardIdentification>(`/images/${imageId}/identify`, { method: "POST" }),
  createCardFromImage: (imageId: string, overrides: Partial<CardInstance>) =>
    request<CardInstance>(`/images/${imageId}/create-card`, {
      method: "POST",
      body: JSON.stringify({ overrides })
    }),
  cards: () => request<CardInstance[]>("/cards"),
  createCard: (payload: Partial<CardInstance>) =>
    request<CardInstance>("/cards", { method: "POST", body: JSON.stringify(payload) }),
  approveCard: (cardId: string) =>
    request<CardInstance>(`/cards/${cardId}/approve`, { method: "POST" }),
  jobs: () => request<JobRecord[]>("/jobs"),
  cancelJob: (jobId: string) => request<JobRecord>(`/jobs/${jobId}/cancel`, { method: "POST" }),
  retryJob: (jobId: string) => request<JobRecord>(`/jobs/${jobId}/retry`, { method: "POST" }),
  exportListings: () =>
    request<ExportResult>("/exports/listings", { method: "POST", body: JSON.stringify({}) }),
  exportLots: () => request<ExportResult>("/exports/lots", { method: "POST", body: JSON.stringify({}) }),
  exportFilePlan: () =>
    request<ExportResult>("/exports/file-plan", { method: "POST", body: JSON.stringify({}) }),
  ebayStatus: () => request<EbayStatus>("/ebay/status"),
  ebayConnect: () => request<EbayConnectResponse>("/ebay/connect", { method: "POST" }),
  ebaySync: (params?: EbaySyncParams) =>
    request<EbayListingSyncResponse>(ebaySyncPath("/ebay/sync", params), { method: "POST" }),
  ebayListings: (params?: EbaySyncParams) => request<EbayListingSyncResponse>(ebaySyncPath("/ebay/listings", params))
};

export function formatCapabilityStatus(status: string): string {
  return status.replace(/_/g, " ");
}
