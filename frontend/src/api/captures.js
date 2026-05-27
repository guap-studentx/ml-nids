import { API_BASE_URL, WS_BASE_URL, apiFetch, getAccessToken } from "./client";

export function listCaptures(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      search.set(key, value);
    }
  });
  const query = search.toString();
  return apiFetch(`/captures${query ? `?${query}` : ""}`);
}

export function getCapture(id) {
  return apiFetch(`/captures/${id}`);
}

export function getCaptureAnalytics(id) {
  return apiFetch(`/captures/${id}/analytics`);
}

export function createReport(id, format = "pdf") {
  return apiFetch(`/captures/${id}/report`, {
    method: "POST",
    body: JSON.stringify({ format }),
  });
}

export function deleteCapture(id) {
  return apiFetch(`/captures/${id}`, {
    method: "DELETE",
  });
}

export function stopCapture(id) {
  return apiFetch(`/captures/${id}/stop`, {
    method: "POST",
  });
}

export function listFlows(id, params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      search.set(key, value);
    }
  });
  const query = search.toString();
  return apiFetch(`/captures/${id}/flows${query ? `?${query}` : ""}`);
}

export function getFlowDetail(captureId, flowId) {
  return apiFetch(`/captures/${captureId}/flows/${flowId}`);
}

export function captureWebSocketUrl(id) {
  const token = encodeURIComponent(getAccessToken() ?? "");
  return `${WS_BASE_URL}/ws/captures/${id}?token=${token}`;
}

export function uploadCsvCapture({ file, modelId, name }) {
  const form = new FormData();
  form.set("file", file);
  form.set("model_id", modelId);
  if (name) {
    form.set("name", name);
  }

  return apiFetch("/captures/upload-csv", {
    method: "POST",
    body: form,
  });
}

export function uploadPcapCapture({ file, modelId, name }) {
  const form = new FormData();
  form.set("file", file);
  form.set("model_id", modelId);
  if (name) {
    form.set("name", name);
  }

  return apiFetch("/captures/upload-pcap", {
    method: "POST",
    body: form,
  });
}

export function startLiveCapture({ name, modelId, agentId, iface, bpfFilter, durationSeconds }) {
  return apiFetch("/captures/live", {
    method: "POST",
    body: JSON.stringify({
      name: name || null,
      model_id: modelId,
      agent_id: agentId,
      iface,
      bpf_filter: bpfFilter || null,
      duration_seconds: Number(durationSeconds),
    }),
  });
}

export async function downloadFlowsCsv(id) {
  const response = await fetch(`${API_BASE_URL}/captures/${id}/flows/export?format=csv`, {
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
    },
  });

  if (!response.ok) {
    throw new Error("Export failed");
  }

  return response.blob();
}
