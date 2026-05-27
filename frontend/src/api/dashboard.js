import { apiFetch } from "./client";

export function getDashboardSummary() {
  return apiFetch("/dashboard/summary");
}

export function getDashboardTimeseries(period = "24h") {
  return apiFetch(`/dashboard/timeseries?period=${period}`);
}
