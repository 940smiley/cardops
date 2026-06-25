export const CARDOPS_APP_NAME = "CardOps AI";

export type ProviderStatus = "available" | "configured" | "disabled" | "missing_credentials" | "restricted";

export function formatCount(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}
