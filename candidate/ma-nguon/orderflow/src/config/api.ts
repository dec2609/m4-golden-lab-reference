/**
 * API Configuration for OrderFlow Frontend
 * Resolves base URL dynamically:
 * 1. import.meta.env.VITE_API_URL (if explicitly provided)
 * 2. In Vite development environment (port 5173): uses '/api' proxy or 'http://127.0.0.1:8081'
 * 3. In production: uses relative '/api' via reverse proxy (e.g. Nginx)
 */
export function getApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === "string" && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, "");
  }

  // If in browser development mode
  if (typeof window !== "undefined" && window.location.port === "5173") {
    // When Vite dev server proxy is enabled, '/api' routes to backend port 8081
    return "/api";
  }

  // Default to relative reverse proxy path
  return "/api";
}
