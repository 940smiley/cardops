import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/health", async (route) => {
    await route.fulfill({
      json: { status: "ok", database: "ok", demo_mode: true, version: "0.1.0" }
    });
  });
  await page.route("**/system/capabilities", async (route) => {
    await route.fulfill({
      json: {
        local_only_mode: true,
        cloud_ai_enabled: false,
        live_ebay_publishing_enabled: false,
        physical_file_moves_enabled: false,
        providers: [
          {
            name: "MockEbayProvider",
            status: "available",
            capabilities: ["offline listing fixtures"],
            limitations: []
          }
        ]
      }
    });
  });
  await page.route("**/cards", async (route) => {
    await route.fulfill({
      json: [
        {
          id: "1",
          internal_sku: "COA-000001",
          sport: "baseball",
          player: "Alex Rivera",
          team: "Chicago Lakes",
          manufacturer: "Northstar",
          brand: "Stadium Line",
          set_name: "Stadium Line",
          set_year: 1991,
          card_number: "42",
          subset: null,
          variation: null,
          parallel: null,
          rookie: false,
          autograph: false,
          relic: false,
          serial_number_current: null,
          serial_number_total: null,
          raw_or_graded: "raw",
          grading_company: null,
          grade: null,
          quantity: 1,
          condition_notes: null,
          acquisition_cost: null,
          estimated_value: 8,
          storage_location: null,
          processing_status: "manual",
          confidence: 0.9,
          tags: ["demo"],
          created_at: "2026-06-23T00:00:00Z",
          updated_at: "2026-06-23T00:00:00Z"
        }
      ]
    });
  });
  await page.route("**/images", async (route) => {
    await route.fulfill({ json: [] });
  });
  await page.route("**/directories", async (route) => {
    await route.fulfill({ json: [] });
  });
  await page.route("**/jobs", async (route) => {
    await route.fulfill({ json: [] });
  });
  await page.route("**/settings", async (route) => {
    await route.fulfill({
      json: {
        local_only_mode: true,
        cloud_ai_enabled: false,
        live_ebay_publishing_enabled: false,
        physical_file_moves_enabled: false,
        daily_ai_request_limit: 0,
        daily_ai_cost_limit: 0,
        updated_at: "2026-06-23T00:00:00Z"
      }
    });
  });
});

test("dashboard and inventory are navigable", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "CardOps AI" })).toBeVisible();
  await expect(page.getByText("Total card instances")).toBeVisible();
  await page.getByRole("button", { name: /Inventory/ }).click();
  await expect(page.getByRole("heading", { name: "Inventory" })).toBeVisible();
  await expect(page.getByText("Alex Rivera")).toBeVisible();
});
