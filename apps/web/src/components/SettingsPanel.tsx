import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, formatCapabilityStatus } from "../api";
import type { SettingsRecord, SystemCapabilities } from "../types";

export function SettingsPanel({ capabilities }: { capabilities?: SystemCapabilities }) {
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: api.updateSettings,
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: ["settings"] });
      const previous = queryClient.getQueryData<SettingsRecord>(["settings"]);
      if (previous) {
        queryClient.setQueryData<SettingsRecord>(["settings"], {
          ...previous,
          ...payload,
          updated_at: new Date().toISOString()
        });
      }
      return { previous };
    },
    onError: (_error, _payload, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["settings"], context.previous);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      queryClient.invalidateQueries({ queryKey: ["capabilities"] });
      queryClient.invalidateQueries({ queryKey: ["health"] });
    }
  });

  const record = settings.data;
  const update = (payload: Partial<SettingsRecord>) => mutation.mutate(payload);

  return (
    <div className="two-column">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Runtime Controls</h2>
            <p>Local runtime mode and AI behavior.</p>
          </div>
        </div>
        {record && (
          <div className="settings-list">
            <Toggle
              label="Demo mode"
              checked={record.demo_mode}
              onChange={(checked) => update({ demo_mode: checked })}
            />
            <Toggle
              label="Local-only mode"
              checked={record.local_only_mode}
              onChange={(checked) => update({ local_only_mode: checked })}
            />
            <Toggle
              label="Cloud AI opt-in"
              checked={record.cloud_ai_enabled}
              onChange={(checked) => update({ cloud_ai_enabled: checked })}
            />
            <SettingsNumberInput
              label="Daily AI request limit"
              min={0}
              value={record.daily_ai_request_limit}
              onCommit={(value) => update({ daily_ai_request_limit: value })}
            />
            <SettingsNumberInput
              label="Daily AI cost limit"
              min={0}
              step={0.01}
              value={record.daily_ai_cost_limit}
              onCommit={(value) => update({ daily_ai_cost_limit: value })}
            />
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Listing Defaults</h2>
            <p>Default recommendation behavior for listing exports.</p>
          </div>
        </div>
        {record && (
          <div className="settings-list">
            <label className="field">
              <span>Default listing format</span>
              <select
                value={record.default_listing_format}
                onChange={(event) =>
                  update({
                    default_listing_format: event.currentTarget
                      .value as SettingsRecord["default_listing_format"]
                  })
                }
              >
                <option value="fixed_price">Fixed price</option>
                <option value="auction">Auction</option>
                <option value="auction_or_lot">Auction or lot</option>
              </select>
            </label>
            <SettingsNumberInput
              label="Confidence threshold"
              min={0}
              max={1}
              step={0.01}
              value={record.confidence_threshold}
              onCommit={(value) => update({ confidence_threshold: value })}
            />
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>eBay Listing Output</h2>
            <p>Choose file export or direct eBay listing mode.</p>
          </div>
        </div>
        {record && (
          <div className="settings-list">
            <label className="field">
              <span>Listing output mode</span>
              <select
                value={record.listing_export_mode}
                onChange={(event) =>
                  update({ listing_export_mode: event.currentTarget.value as SettingsRecord["listing_export_mode"] })
                }
              >
                <option value="file_upload">CSV file for manual upload</option>
                <option value="ebay_direct">Direct eBay listing mode</option>
              </select>
            </label>
            <Toggle
              label="Direct eBay listing enable"
              checked={record.ebay_direct_listing_enabled}
              onChange={(checked) => update({ ebay_direct_listing_enabled: checked })}
            />
            <Toggle
              label="Live eBay publishing"
              checked={record.live_ebay_publishing_enabled}
              onChange={(checked) => update({ live_ebay_publishing_enabled: checked })}
            />
            <SettingsTextInput
              label="Marketplace ID"
              value={record.ebay_marketplace_id}
              onCommit={(value) => update({ ebay_marketplace_id: value })}
            />
            <SettingsTextInput
              label="Merchant location key"
              value={record.ebay_merchant_location_key}
              onCommit={(value) => update({ ebay_merchant_location_key: value })}
            />
            <SettingsTextInput
              label="Payment policy ID"
              value={record.ebay_payment_policy_id}
              onCommit={(value) => update({ ebay_payment_policy_id: value })}
            />
            <SettingsTextInput
              label="Return policy ID"
              value={record.ebay_return_policy_id}
              onCommit={(value) => update({ ebay_return_policy_id: value })}
            />
            <SettingsTextInput
              label="Fulfillment policy ID"
              value={record.ebay_fulfillment_policy_id}
              onCommit={(value) => update({ ebay_fulfillment_policy_id: value })}
            />
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>eBay Sync Defaults</h2>
            <p>Read-only Inventory API fetch controls.</p>
          </div>
        </div>
        {record && (
          <div className="settings-list">
            <SettingsNumberInput
              label="Sync page size"
              min={1}
              max={200}
              value={record.ebay_sync_limit}
              onCommit={(value) => update({ ebay_sync_limit: value })}
            />
            <SettingsNumberInput
              label="Sync offset"
              min={0}
              value={record.ebay_sync_offset}
              onCommit={(value) => update({ ebay_sync_offset: value })}
            />
            <Toggle
              label="Include offer lookup"
              checked={record.ebay_sync_include_offers}
              onChange={(checked) => update({ ebay_sync_include_offers: checked })}
            />
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>OCR and Paths</h2>
            <p>Local OCR executable and export locations.</p>
          </div>
        </div>
        {record && (
          <div className="settings-list">
            <SettingsTextInput
              label="Tesseract command"
              value={record.tesseract_cmd}
              onCommit={(value) => update({ tesseract_cmd: value })}
            />
            <SettingsTextInput
              label="OCR language"
              value={record.ocr_language}
              onCommit={(value) => update({ ocr_language: value })}
            />
            <SettingsTextInput
              label="Default input directory"
              value={record.default_input_dir}
              onCommit={(value) => update({ default_input_dir: value })}
            />
            <SettingsTextInput
              label="Default output directory"
              value={record.default_output_dir}
              onCommit={(value) => update({ default_output_dir: value })}
            />
            <SettingsTextInput
              label="Inventory CSV path"
              value={record.default_inventory_path}
              onCommit={(value) => update({ default_inventory_path: value })}
            />
            <SettingsTextInput
              label="eBay listing CSV path"
              value={record.default_ebay_export_path}
              onCommit={(value) => update({ default_ebay_export_path: value })}
            />
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>File Operations</h2>
            <p>Physical file actions remain opt-in.</p>
          </div>
        </div>
        {record && (
          <div className="settings-list">
            <Toggle
              label="Physical file moves"
              checked={record.physical_file_moves_enabled}
              onChange={(checked) => update({ physical_file_moves_enabled: checked })}
            />
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Capability Matrix</h2>
            <p>Provider status is based on local configuration and detection.</p>
          </div>
        </div>
        <div className="provider-list">
          {capabilities?.providers.map((provider) => (
            <div className="provider-row" key={provider.name}>
              <div>
                <strong>{provider.name}</strong>
                <span>{provider.limitations[0] ?? provider.capabilities.join(", ")}</span>
              </div>
              <span className={`status-chip ${provider.status}`}>{formatCapabilityStatus(provider.status)}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Toggle({
  label,
  checked,
  onChange
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  const [localChecked, setLocalChecked] = useState(checked);

  useEffect(() => {
    setLocalChecked(checked);
  }, [checked]);

  return (
    <label className="toggle-row">
      <span>{label}</span>
      <input
        type="checkbox"
        checked={localChecked}
        onChange={(event) => {
          const next = event.currentTarget.checked;
          setLocalChecked(next);
          onChange(next);
        }}
      />
    </label>
  );
}

function SettingsTextInput({
  label,
  value,
  onCommit
}: {
  label: string;
  value: string | null;
  onCommit: (value: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        key={`${label}:${value ?? ""}`}
        type="text"
        defaultValue={value ?? ""}
        onBlur={(event) => {
          if (event.currentTarget.value !== (value ?? "")) {
            onCommit(event.currentTarget.value);
          }
        }}
      />
    </label>
  );
}

function SettingsNumberInput({
  label,
  value,
  min,
  max,
  step = 1,
  onCommit
}: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onCommit: (value: number) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        key={`${label}:${value}`}
        type="number"
        min={min}
        max={max}
        step={step}
        defaultValue={value}
        onBlur={(event) => {
          const next = Number(event.currentTarget.value);
          if (Number.isFinite(next) && next !== value) {
            onCommit(next);
          }
        }}
      />
    </label>
  );
}
