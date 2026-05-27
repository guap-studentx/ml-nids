import { apiFetch } from "./client";

export function listAgents() {
  return apiFetch("/agents");
}

export function createAgent(name) {
  return apiFetch("/agents", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function deleteAgent(id) {
  return apiFetch(`/agents/${id}`, {
    method: "DELETE",
  });
}

export function getAgentIfaces(id) {
  return apiFetch(`/agents/${id}/ifaces`);
}
