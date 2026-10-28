import { getJson } from "./jsonTransport";
import { getApiBaseUrl } from "../config/api";
import { ApiError } from "./apiError";

export interface ReadinessObservation {
  state: "READY" | "UNREADY" | "NOT_IMPLEMENTED" | "ERROR";
  origin: "HTTP" | "SIMULATED";
  observedAt: string;
}
/** PR14 M4 /ready contract; 404 remains an unavailable legacy-backend observation. */
export async function checkReadiness(options: {
  signal?: AbortSignal; fetch?: typeof fetch; timeoutMs?: number;
  baseUrl?: string; simulated?: boolean;
} = {}): Promise<ReadinessObservation> {
  const response = await getJson((options.baseUrl ?? getApiBaseUrl()) + "/ready", {
    signal: options.signal, fetch: options.fetch, timeoutMs: options.timeoutMs,
    statuses: [200, 503, 404], noBodyStatuses: [404],
  });
  const base = { origin: options.simulated ? "SIMULATED" as const : "HTTP" as const, observedAt: new Date().toISOString() };
  if (response.status === 404) return { ...base, state: "NOT_IMPLEMENTED" };
  const body = response.body;
  if (!body || typeof body !== "object" || Array.isArray(body)) throw new ApiError("Invalid M4 readiness response.", { kind: "contract" });
  const data = body as Record<string, unknown>;
  if (response.status === 200 && data.status === "ready" && data.database === "connected" && data.error === undefined) return { ...base, state: "READY" };
  if (response.status === 503 && data.status === "unready" && typeof data.error === "string" && data.error.trim() && data.database !== "connected") return { ...base, state: "UNREADY" };
  throw new ApiError("Readiness response contradicts the M4 contract; DB readiness is not confirmed.", { kind: "contract" });
}
