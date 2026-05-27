import { apiFetch } from "./client";

export function listModels() {
  return apiFetch("/models");
}

export function getModel(id) {
  return apiFetch(`/models/${id}`);
}

export function uploadModel({ file, modelId, displayName }) {
  const form = new FormData();
  form.set("file", file);
  if (modelId) {
    form.set("model_id", modelId);
  }
  if (displayName) {
    form.set("display_name", displayName);
  }
  return apiFetch("/models/upload", {
    method: "POST",
    body: form,
  });
}

export function updateModel(id, payload) {
  return apiFetch(`/models/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteModel(id) {
  return apiFetch(`/models/${id}`, {
    method: "DELETE",
  });
}
