import { API_BASE_URL, apiFetch, getAccessToken } from "./client";

export function listReports(params = {}) {
  const search = new URLSearchParams(params);
  const query = search.toString();
  return apiFetch(`/reports${query ? `?${query}` : ""}`);
}

export async function downloadReport(id) {
  const response = await fetch(`${API_BASE_URL}/reports/${id}/download`, {
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
    },
  });

  if (!response.ok) {
    throw new Error("Report download failed");
  }

  return response.blob();
}
