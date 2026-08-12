import axios from "axios";

// Relative by default so the built bundle works behind any domain/IP without
// a rebuild -- nginx.conf reverse-proxies /api (and /static, /admin) to the
// backend under the same origin the page was served from. Set VITE_API_URL
// at build time only if the frontend is ever served from a different origin
// than the backend (e.g. local `npm run dev` against a remote API).
export const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

export const api = axios.create({ baseURL: API_BASE });

const TOKEN_KEY = "operatordesk_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/** Builds a ws(s):// URL for a path under the API base, e.g. wsUrl("/ws/notifications").
 * Keeps the "/api" prefix from API_BASE -- the backend registers the ws route
 * under the same "/api" router prefix as every REST route. Resolves a relative
 * API_BASE (the default) against the page's own origin, since a relative path
 * has no scheme/host for the ws()/wss() rewrite to work on directly. */
export function wsUrl(path: string): string {
  const base = API_BASE.replace(/\/$/, "");
  if (/^https?:\/\//.test(base)) {
    return `${base.replace(/^http/, "ws")}${path}`;
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${base}${path}`;
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken();
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);
