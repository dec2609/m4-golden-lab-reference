import type { ReleaseStatus } from "../types/release";
import {
  getReleaseScenario, mockReleaseInvalid, mockReleaseV1Pass, mockReleaseV1Blocked,
  mockReleaseV2Pass, mockReleaseV2Blocked, mockReleaseV2Rollback, setReleaseScenario,
  type ReleaseScenario,
} from "../mocks/release";

export type { ReleaseScenario };
export interface ReleaseValidationResult {
  isValid: boolean;
  errorReason?: string;
  data?: ReleaseStatus;
  schemaVersion?: 1 | 2;
}
const REQUIRED_CONTROLS_V1 = ["GITLEAKS_STATUS", "DEPENDENCY_STATUS", "UNIT_TEST_STATUS", "SBOM_STATUS", "DIGEST_STATUS", "COSIGN_STATUS"] as const;
const REQUIRED_CONTROLS_V2 = [...REQUIRED_CONTROLS_V1, "VULNERABILITY_STATUS", "REGISTRY_STATUS"] as const;
const record = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === "object" && !Array.isArray(value);
const matches = (value: unknown, pattern: RegExp) => typeof value === "string" && pattern.test(value);
const digest = /^sha256:[0-9a-f]{64}$/;
const status = (value: unknown) => value === "PASS" || value === "FAIL";
const invalid = (reason: string): ReleaseValidationResult => ({ isValid: false, errorReason: reason });
const imageReference = /^(?:[a-z0-9]+(?:[._-][a-z0-9]+)*(?::[0-9]+)?\/)?[a-z0-9]+(?:[._\/-][a-z0-9]+)*(?::[A-Za-z0-9_][A-Za-z0-9_.-]{0,127})?(?:@sha256:[0-9a-f]{64})?$/;

/** Consumer safety checks, not authentication or a replacement for Quang's v2 schema. */
export function validateReleaseStatus(data: unknown): ReleaseValidationResult {
  if (!record(data)) return invalid("Release payload must be a JSON object.");
  if (data.schema_version !== 1 && data.schema_version !== 2) return invalid("Missing or unsupported schema_version (expected 1 or 2).");
  if (!matches(data.source_commit, /^[0-9a-f]{40}$/)) return invalid("Invalid source_commit: expected 40 lowercase hexadecimal characters.");
  if (!matches(data.artifact_sha256, /^[0-9a-f]{64}$/)) return invalid("Invalid artifact_sha256: expected 64 lowercase hexadecimal characters.");
  if (!matches(data.image_digest, digest)) return invalid("Invalid image_digest: expected sha256:<64 lowercase hexadecimal characters>.");
  if (!record(data.controls)) return invalid("Missing or invalid controls object.");
  const controls = data.controls;
  const required = data.schema_version === 1 ? REQUIRED_CONTROLS_V1 : REQUIRED_CONTROLS_V2;
  for (const key of required) {
    if (!Object.prototype.hasOwnProperty.call(controls, key) || !status(controls[key])) return invalid(`Missing or invalid control status for ${key}. Expected PASS | FAIL.`);
  }
  if (data.schema_version === 1) {
    // Match the existing group's schema v1 additionalProperties:false rules.
    const fields = ["schema_version", "source_commit", "artifact_sha256", "image_digest", "controls", "PRODUCTION_GATE"];
    if (Object.keys(data).some((key) => !fields.includes(key)) || Object.keys(controls).some((key) => !REQUIRED_CONTROLS_V1.includes(key as typeof REQUIRED_CONTROLS_V1[number]))) {
      return invalid("Unknown field in schema v1 payload or controls.");
    }
  }
  if (data.PRODUCTION_GATE !== "PASS" && data.PRODUCTION_GATE !== "BLOCKED") return invalid("Invalid PRODUCTION_GATE: expected PASS | BLOCKED.");
  if (data.PRODUCTION_GATE === "PASS" && required.some((key) => controls[key] !== "PASS")) {
    return invalid("Contract violation: PRODUCTION_GATE PASS requires every mandatory control to be PASS.");
  }

  if (data.schema_version === 2) {
    if (!record(data.registry)) return invalid("Missing or invalid registry metadata: expected an object.");
    const reg = data.registry;
    if (!matches(reg.image_digest, digest)) return invalid("Missing or invalid registry.image_digest.");
    if (!matches(reg.image_reference, imageReference)) return invalid("Missing or invalid registry.image_reference.");
    if (controls.REGISTRY_STATUS === "PASS") {
      if (data.registry.image_digest !== data.image_digest) return invalid("Contract violation: registry PASS requires matching payload digests; this comparison does not verify a registry.");
      const reference = data.registry.image_reference as string;
      if (reference.includes("@") && reference.split("@")[1] !== data.registry.image_digest) return invalid("Contract violation: digest in image reference disagrees with registry.image_digest.");
    }
    if (!record(data.deployment)) return invalid("Missing or invalid deployment metadata: expected an object.");
    const dep = data.deployment;
    if (dep.DEPLOYMENT_GATE !== "PASS" && dep.DEPLOYMENT_GATE !== "FAIL" && dep.DEPLOYMENT_GATE !== "NOT_RUN") return invalid("Missing or invalid DEPLOYMENT_GATE.");
    for (const key of ["READINESS_STATUS", "API_STATUS"]) {
      if (!status(dep[key]) && dep[key] !== "NOT_RUN") return invalid(`Missing or invalid ${key}.`);
    }
    if (typeof dep.ROLLBACK_STATUS !== "string" || !["PASS", "FAIL", "NOT_REQUIRED"].includes(dep.ROLLBACK_STATUS)) return invalid("Missing or invalid ROLLBACK_STATUS.");
    if (dep.DEPLOYMENT_GATE === "NOT_RUN" && (dep.READINESS_STATUS !== "NOT_RUN" || dep.API_STATUS !== "NOT_RUN" || dep.ROLLBACK_STATUS !== "NOT_REQUIRED")) {
      return invalid("Contract violation: deployment NOT_RUN requires both probes NOT_RUN and rollback NOT_REQUIRED.");
    }
    if (dep.DEPLOYMENT_GATE === "FAIL" && (dep.READINESS_STATUS === "NOT_RUN" || dep.API_STATUS === "NOT_RUN")) {
      return invalid("Partial probe execution for failed deployment requires producer contract confirmation.");
    }
    if (dep.DEPLOYMENT_GATE === "PASS" && (data.PRODUCTION_GATE !== "PASS" || dep.READINESS_STATUS !== "PASS" || dep.API_STATUS !== "PASS")) {
      return invalid("Contract violation: deployment PASS requires production, readiness and API PASS.");
    }
    if ((dep.ROLLBACK_STATUS === "PASS" || dep.ROLLBACK_STATUS === "FAIL") && (data.PRODUCTION_GATE !== "PASS" || dep.DEPLOYMENT_GATE !== "FAIL")) {
      return invalid("Contradictory rollback result; attempted rollout/rollback semantics require producer confirmation.");
    }
  }
  return { isValid: true, data: data as unknown as ReleaseStatus, schemaVersion: data.schema_version };
}

/** Parse transport JSON without treating a valid payload as authenticated evidence. */
export function validateReleaseJson(text: string): ReleaseValidationResult {
  try { return validateReleaseStatus(JSON.parse(text)); } catch { return invalid("Release response is malformed JSON."); }
}

// Preparation only. No URL, trust policy or producer v2 contract is assumed here.
export interface ReleaseEvidenceSource {
  description: string;
  read(signal?: AbortSignal): Promise<unknown>;
}
export async function inspectReleaseEvidence(source: ReleaseEvidenceSource, signal?: AbortSignal) {
  try {
    const payload = await source.read(signal);
    if (signal?.aborted) return { ...invalid("Evidence load was cancelled."), source: source.description, authenticity: "UNVERIFIED" as const };
    return { ...validateReleaseStatus(payload), source: source.description, authenticity: "UNVERIFIED" as const };
  } catch {
    return { ...invalid("Release evidence source unavailable."), source: source.description, authenticity: "UNVERIFIED" as const };
  }
}

export interface ReleaseService {
  getReleaseStatus(): Promise<unknown>;
  validateRelease(data: unknown): ReleaseValidationResult;
  setScenario(scenario: ReleaseScenario): void;
  getScenario(): ReleaseScenario;
}
let releaseRevision = 0;
export const releaseService: ReleaseService = {
  async getReleaseStatus() {
    const scenario = getReleaseScenario();
    const revision = releaseRevision;
    await new Promise((resolve) => setTimeout(resolve, 300));
    if (revision !== releaseRevision || scenario !== getReleaseScenario()) throw new Error("Release fixture selection changed; stale result discarded.");
    switch (scenario) {
      case "pass": return structuredClone(mockReleaseV1Pass);
      case "blocked": return structuredClone(mockReleaseV1Blocked);
      case "v2-pass": return structuredClone(mockReleaseV2Pass);
      case "v2-blocked": return structuredClone(mockReleaseV2Blocked);
      case "v2-rollback": return structuredClone(mockReleaseV2Rollback);
      case "invalid": return structuredClone(mockReleaseInvalid);
      default: throw new Error("Release fixture unavailable.");
    }
  },
  validateRelease: validateReleaseStatus,
  setScenario(scenario) { releaseRevision++; setReleaseScenario(scenario); },
  getScenario: getReleaseScenario,
};
