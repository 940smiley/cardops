export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

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
  estimated_value: number | null;
  processing_status: string;
  confidence: number | null;
  tags: string[];
}
