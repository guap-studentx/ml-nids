import { apiFetch } from "./client";

export function listLiveSessions(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      search.set(key, value);
    }
  });
  const query = search.toString();
  return apiFetch(`/live-sessions${query ? `?${query}` : ""}`);
}

export function createLiveSession({ name, agentId, iface, modelId, bpfFilter, chunkSeconds, durationSeconds }) {
  return apiFetch("/live-sessions", {
    method: "POST",
    body: JSON.stringify({
      name: name || null,
      agent_id: agentId,
      iface,
      model_id: modelId,
      bpf_filter: bpfFilter || null,
      chunk_seconds: Number(chunkSeconds),
      duration_seconds: Number(durationSeconds),
    }),
  });
}

export function getLiveSession(id) {
  return apiFetch(`/live-sessions/${id}`);
}

export function listLiveSessionChunks(id) {
  return apiFetch(`/live-sessions/${id}/chunks`);
}

export function stopLiveSession(id) {
  return apiFetch(`/live-sessions/${id}/stop`, {
    method: "POST",
  });
}

export function deleteLiveSession(id) {
  return apiFetch(`/live-sessions/${id}`, {
    method: "DELETE",
  });
}
