import { useMutation, useQuery, type UseMutationResult } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { api } from "../api";
import type { ExportResult } from "../types";

function ExportButton({
  label,
  mutation
}: {
  label: string;
  mutation: UseMutationResult<ExportResult, Error, void>;
}) {
  return (
    <div className="provider-row">
      <div>
        <strong>{label}</strong>
        <span>
          {mutation.data
            ? `${mutation.data.row_count} rows -> ${mutation.data.message ?? mutation.data.path ?? mutation.data.delivery_mode}`
            : "Ready"}
        </span>
      </div>
      <button className="secondary-button" type="button" disabled={mutation.isPending} onClick={() => mutation.mutate()}>
        <Download size={15} />
        Export
      </button>
    </div>
  );
}

export function ExportsPanel() {
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const listings = useMutation<ExportResult, Error, void>({ mutationFn: () => api.exportListings() });
  const lots = useMutation<ExportResult, Error, void>({ mutationFn: () => api.exportLots() });
  const filePlan = useMutation<ExportResult, Error, void>({ mutationFn: () => api.exportFilePlan() });
  const listingMode = settings.data?.listing_export_mode ?? "file_upload";
  const listingLabel =
    listingMode === "ebay_direct" ? "eBay direct listing export" : "eBay-ready listing CSV";

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Imports and Exports</h2>
          <p>Generate local files or route listing output through configured eBay mode.</p>
        </div>
      </div>
      <div className="provider-list">
        <ExportButton label={listingLabel} mutation={listings} />
        <ExportButton label="Lot assignment CSV" mutation={lots} />
        <ExportButton label="Safe file-plan CSV" mutation={filePlan} />
      </div>
      {[listings, lots, filePlan].map((mutation, index) =>
        mutation.error ? <p className="form-error" key={index}>{mutation.error.message}</p> : null
      )}
    </section>
  );
}
