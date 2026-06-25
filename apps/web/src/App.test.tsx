import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { formatCapabilityStatus } from "./api";

vi.stubGlobal(
  "fetch",
  vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = url.endsWith("/health")
      ? { status: "ok", database: "ok", demo_mode: true, version: "0.1.0" }
      : url.endsWith("/system/capabilities")
        ? {
            demo_mode: true,
            local_only_mode: true,
            cloud_ai_enabled: false,
            live_ebay_publishing_enabled: false,
            physical_file_moves_enabled: false,
            listing_export_mode: "file_upload",
            ebay_direct_listing_enabled: false,
            ebay_sync_limit: 25,
            ebay_sync_offset: 0,
            ebay_sync_include_offers: true,
            default_listing_format: "fixed_price",
            confidence_threshold: 0.72,
            providers: [{ name: "MockEbayProvider", status: "available", capabilities: ["mock"], limitations: [] }]
          }
        : url.endsWith("/cards")
          ? []
            : url.endsWith("/images")
            ? []
            : url.endsWith("/directories")
              ? []
              : url.endsWith("/jobs")
                ? []
                : {
                    demo_mode: true,
                    local_only_mode: true,
                    cloud_ai_enabled: false,
                    live_ebay_publishing_enabled: false,
                    physical_file_moves_enabled: false,
                    listing_export_mode: "file_upload",
                    ebay_direct_listing_enabled: false,
                    ebay_marketplace_id: "EBAY_US",
                    ebay_merchant_location_key: null,
                    ebay_payment_policy_id: null,
                    ebay_return_policy_id: null,
                    ebay_fulfillment_policy_id: null,
                    ebay_sync_limit: 25,
                    ebay_sync_offset: 0,
                    ebay_sync_include_offers: true,
                    default_listing_format: "fixed_price",
                    confidence_threshold: 0.72,
                    tesseract_cmd: "E:\\Apps\\tesseract-ocr\\tesseract.exe",
                    ocr_language: "eng",
                    default_input_dir: null,
                    default_output_dir: "./data/exports",
                    default_inventory_path: "./data/exports/cardops-inventory.csv",
                    default_ebay_export_path: "./data/exports/cardops-ebay-listings.csv",
                    daily_ai_request_limit: 0,
                    daily_ai_cost_limit: 0,
                    updated_at: new Date().toISOString()
                  };
    return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
  })
);

describe("App", () => {
  it("renders the operations dashboard", async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    );
    expect(await screen.findByRole("heading", { name: "CardOps AI" })).toBeInTheDocument();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Total card instances")).toBeInTheDocument();
  });

  it("formats capability statuses", () => {
    expect(formatCapabilityStatus("missing_credentials")).toBe("missing credentials");
  });
});
