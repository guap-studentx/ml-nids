import { apiFetch } from "./client";

export function login(username, password) {
  return apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function getCurrentUser() {
  return apiFetch("/auth/me");
}
