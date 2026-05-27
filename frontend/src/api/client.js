export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");

let accessToken = localStorage.getItem("ml_nids_token");

export function setAccessToken(token) {
  accessToken = token;
  if (token) {
    localStorage.setItem("ml_nids_token", token);
  } else {
    localStorage.removeItem("ml_nids_token");
  }
}

export function getAccessToken() {
  return accessToken;
}

export async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers ?? {});
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const message = errorMessage(data);
    throw new Error(message);
  }

  return data;
}

function errorMessage(data) {
  if (typeof data === "string" && data) {
    return data;
  }
  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item) => {
        const location = Array.isArray(item.loc) ? item.loc.join(".") : "request";
        return `${location}: ${item.msg}`;
      })
      .join("; ");
  }
  if (typeof data?.detail === "string") {
    return data.detail;
  }
  return "Request failed";
}
