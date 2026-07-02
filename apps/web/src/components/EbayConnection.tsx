import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, RefreshCw, Unplug } from "lucide-react";
import { useState } from "react";
import { api, formatCapabilityStatus } from "../api";
import type { EbayConnectResponse, EbayListingSyncResponse } from "../types";

function countRecords(
  value:
    | {
        total?: number;
        size?: number;
        inventoryItems?: unknown[];
        offers?: unknown[];
      }
    | null
    | undefined,
  key: "inventoryItems" | "offers"
) {
  if (!value) {
    return 0;
  }
  const records = value[key];
  if (Array.isArray(records)) {
    return records.length;
  }
  return value.total ?? value.size ?? 0;
}

function openAuthorizationWindow(response: EbayConnectResponse) {
  if (response.authorization_url) {
    window.open(response.authorization_url, "_blank", "noopener,noreferrer");
  }
}

export function EbayConnection() {
  const queryClient = useQueryClient();
  const [lastAction, setLastAction] = useState<string | null>(null);
  const status = useQuery({
    queryKey: ["ebay-status"],
    queryFn: api.ebayStatus,
    refetchInterval: 5000
  });
  const connect = useMutation({
    mutationFn: api.ebayConnect,
    onSuccess: (data) => {
      openAuthorizationWindow(data);
      setLastAction("Opened eBay authorization in a new browser tab. This panel checks connection status every few seconds.");
      queryClient.invalidateQueries({ queryKey: ["ebay-status"] });
    }
  });
  const sync = useMutation({
    mutationFn: () => api.ebaySync(),
    onSuccess: (data) => {
      if (data.state === "authorization_required") {
        setLastAction(data.message ?? "Connect eBay before syncing listings.");
      } else {
        setLastAction("Read-only eBay listing sync completed.");
      }
      queryClient.invalidateQueries({ queryKey: ["ebay-status"] });
    }
  });

  const record = status.data;
  const syncResult = sync.data;
  const inventoryCount = countRecords(syncResult?.inventory, "inventoryItems");
  const offerCount = countRecords(syncResult?.offers ?? undefined, "offers");
  const offerErrors = syncResult?.offers?.errors ?? [];
  const inventoryOnlySkus = syncResult?.offers?.inventoryOnlySkus ?? [];
  const isConnected = record?.token.connected ?? false;

  return (
    <div className="two-column">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>eBay Connection</h2>
            <p>Production OAuth and read-only seller inventory sync.</p>
          </div>
          <span className={`status-chip ${record?.state ?? "queued"}`}>
            {formatCapabilityStatus(record?.state ?? "checking")}
          </span>
        </div>

        <div className="provider-list">
          <div className="provider-row">
            <div>
              <strong>Environment</strong>
              <span>{record?.environment ?? "checking"}</span>
            </div>
            <span className={`status-chip ${record?.configured ? "configured" : "missing_credentials"}`}>
              {record?.configured ? "configured" : "missing credentials"}
            </span>
          </div>
          <div className="provider-row">
            <div>
              <strong>OAuth redirect</strong>
              <span>{record?.redirect_uri ?? "checking"}</span>
            </div>
            <span className={`status-chip ${record?.runame_configured ? "configured" : "disabled"}`}>
              {record?.runame_configured ? "RuName" : "URL"}
            </span>
          </div>
          <div className="provider-row">
            <div>
              <strong>Stored token</strong>
              <span>
                access {record?.token.has_access_token ? "stored" : "missing"}, refresh{" "}
                {record?.token.has_refresh_token ? "stored" : "missing"}
              </span>
            </div>
            <span className={`status-chip ${isConnected ? "connected" : "disabled"}`}>
              {isConnected ? "connected" : "not connected"}
            </span>
          </div>
        </div>

        <div className="button-row">
          <button
            className="primary-button"
            type="button"
            disabled={connect.isPending || !record?.configured}
            onClick={() => connect.mutate()}
          >
            <ExternalLink size={15} />
            Connect eBay
          </button>
          <button
            className="secondary-button"
            type="button"
            disabled={sync.isPending || !record?.configured}
            onClick={() => sync.mutate()}
          >
            <RefreshCw size={15} />
            Sync Listings
          </button>
        </div>

        {lastAction && <p className="notice">{lastAction}</p>}
        {connect.error && <p className="form-error">{connect.error.message}</p>}
        {sync.error && <p className="form-error">{sync.error.message}</p>}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Read-only Listing Sync</h2>
            <p>Uses eBay Inventory API after user authorization.</p>
          </div>
          <Unplug size={18} aria-hidden="true" />
        </div>

        <div className="metric-strip ebay-metrics">
          <div className="metric teal">
            <span>Inventory records</span>
            <strong>{inventoryCount}</strong>
          </div>
          <div className="metric amber">
            <span>Offer records</span>
            <strong>{offerCount}</strong>
          </div>
        </div>

        {syncResult?.state === "authorization_required" && syncResult.connect && (
          <div className="notice">
            <strong>Authorization required</strong>
            <span> Complete the eBay consent flow, then run Sync Listings again.</span>
          </div>
        )}

        {syncResult?.state === "synced" && (
          <div className="provider-list">
            <div className="provider-row">
              <div>
                <strong>Provider</strong>
                <span>{syncResult.provider}</span>
              </div>
              <span className="status-chip available">synced</span>
            </div>
            <div className="provider-row">
              <div>
                <strong>Mode</strong>
                <span>{syncResult.read_only ? "read-only" : "write enabled"}</span>
              </div>
              <span className="status-chip configured">{syncResult.environment}</span>
            </div>
            {syncResult.sync_config && (
              <div className="provider-row">
                <div>
                  <strong>Sync defaults</strong>
                  <span>
                    limit {syncResult.sync_config.limit}, offset {syncResult.sync_config.offset}, offers{" "}
                    {syncResult.sync_config.include_offers ? "included" : "skipped"}
                  </span>
                </div>
                <span className="status-chip configured">settings</span>
              </div>
            )}
          </div>
        )}

        {offerErrors.length > 0 && (
          <div className="notice">
            <strong>{offerErrors.length} offer lookup warning{offerErrors.length === 1 ? "" : "s"}</strong>
            <span> {syncResult?.offers?.message ?? "Some SKU offer lookups failed."}</span>
            <ul className="compact-list">
              {offerErrors.slice(0, 5).map((error) => (
                <li key={`${error.sku}:${error.error}`}>
                  <span>{error.sku ?? "unknown SKU"}</span>
                  <small>{error.error}</small>
                </li>
              ))}
            </ul>
          </div>
        )}

        {inventoryOnlySkus.length > 0 && (
          <div className="notice">
            <strong>{inventoryOnlySkus.length} inventory-only SKU{inventoryOnlySkus.length === 1 ? "" : "s"}</strong>
            <span> eBay returned inventory records for these SKUs, but no available offer records.</span>
            <ul className="compact-list">
              {inventoryOnlySkus.slice(0, 8).map((sku) => (
                <li key={sku}>
                  <span>{sku}</span>
                  <small>Inventory item exists; eBay reported no available offer.</small>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="endpoint-list">
          <span>Accepted URL</span>
          <code>{record?.auth_accepted_url ?? "checking"}</code>
          <span>Declined URL</span>
          <code>{record?.auth_declined_url ?? "checking"}</code>
        </div>
      </section>
    </div>
  );
}
