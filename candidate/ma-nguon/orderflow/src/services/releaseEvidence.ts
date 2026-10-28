import { validateReleaseStatus, type ReleaseEvidenceSource } from "./release";
import type { ReleaseStatus } from "../types/release";
import { getJson, sameOriginPath } from "./jsonTransport";

export type EvidenceAuthenticity = "FIXTURE" | "UNVERIFIED" | "VERIFIED";
export interface EvidenceIdentity {
  source_commit?: string; artifact_sha256?: string; image_digest?: string;
}
export interface EvidenceInspection {
  state: "ready" | "empty" | "invalid";
  authenticity: EvidenceAuthenticity;
  source: string;
  data?: ReleaseStatus;
  reason?: string;
  provenance: "MISSING" | "CONSISTENT";
  observedAt: string;
}
export function createHttpEvidenceSource(path: string, options: { fetch?: typeof fetch; timeoutMs?: number } = {}): ReleaseEvidenceSource {
  const endpoint = sameOriginPath(path);
  return {
    description: endpoint,
    async read(signal) {
      return (await getJson(endpoint, { ...options, signal, statuses: [200, 204], noBodyStatuses: [204] })).body;
    },
  };
}

/** Proposed optional provenance extension; consistency/freshness checks are NOT authentication. */
export function inspectEvidence(payload: unknown, context: {
  source: string; fixture?: boolean; expected?: EvidenceIdentity; now?: number; maxAgeMs?: number;
}): EvidenceInspection {
  const now = context.now ?? Date.now();
  const base = { authenticity: context.fixture ? "FIXTURE" as const : "UNVERIFIED" as const,
    source: context.source, observedAt: new Date(now).toISOString(), provenance: "MISSING" as const };
  if (payload === null || payload === undefined) return { ...base, state: "empty", reason: "No release evidence is available." };
  const validation = validateReleaseStatus(payload);
  if (!validation.isValid || !validation.data) return { ...base, state: "invalid", reason: validation.errorReason };
  const data = validation.data;
  const bad = (reason: string): EvidenceInspection => ({ ...base, state: "invalid", reason });
  for (const key of ["source_commit", "artifact_sha256", "image_digest"] as const) {
    const expected = context.expected?.[key];
    if (expected !== undefined && expected !== data[key]) return bad("Expected artifact identity mismatch: " + key + ".");
  }
  const provenance = (payload as Record<string, unknown>).provenance;
  if (provenance !== undefined) {
    if (provenance === null || typeof provenance !== "object" || Array.isArray(provenance)) return bad("Invalid proposed provenance object.");
    const p = provenance as Record<string, unknown>;
    if (typeof p.run_id !== "string" || !p.run_id.trim() || typeof p.generated_at !== "string" ||
        !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(p.generated_at) || !Number.isFinite(Date.parse(p.generated_at)) ||
        new Date(p.generated_at).toISOString().slice(0, 19) !== p.generated_at.slice(0, 19)) {
      return bad("Proposed provenance requires run_id and a UTC generated_at.");
    }
    for (const key of ["source_commit", "artifact_sha256", "image_digest"] as const) {
      if (p[key] !== undefined && p[key] !== data[key]) return bad("Provenance identity mismatch: " + key + ".");
    }
    const age = now - Date.parse(p.generated_at);
    if (age < -60000) return bad("Evidence provenance timestamp is in the future.");
    if (age > (context.maxAgeMs ?? 24 * 60 * 60 * 1000)) return bad("Evidence is stale under the proposed consumer freshness policy.");
    return { ...base, state: "ready", data, provenance: "CONSISTENT" };
  }
  return { ...base, state: "ready", data };
}

export async function readEvidence(source: ReleaseEvidenceSource, options: {
  signal?: AbortSignal; fixture?: boolean; expected?: EvidenceIdentity;
} = {}): Promise<EvidenceInspection> {
  const payload = await source.read(options.signal);
  if (options.signal?.aborted) throw new Error("Evidence selection was cancelled.");
  return inspectEvidence(payload, { source: source.description, fixture: options.fixture, expected: options.expected });
}
// VERIFIED is reserved for a future trusted verifier. No current HTTP/payload/fixture path produces it.
