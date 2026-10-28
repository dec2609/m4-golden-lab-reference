import type { ReleaseStatusV1, ReleaseStatusV2, ReleaseStatus } from "../types/release";

/**
 * [DEMO / MOCK FIXTURE]
 * UI fixtures only for testing and development.
 * This data is NOT technical security evidence.
 */

// --- SCHEMA V1 FIXTURES (6 Controls) ---

export const mockReleaseV1Pass: ReleaseStatusV1 = {
  schema_version: 1,
  source_commit: "7c33671e9f2b4a1d8c6e5f3a2b1d0c9e8f7a6b5c",
  artifact_sha256:
    "8e4f1d2c3b4a59687766554433221100ffeeddccbbaa99887766554433221100",
  image_digest:
    "sha256:91f8c6b7a4d32e10c5f6b7a8d9e0123456789abcdef0123456789abcdef01230",
  controls: {
    GITLEAKS_STATUS: "PASS",
    DEPENDENCY_STATUS: "PASS",
    UNIT_TEST_STATUS: "PASS",
    SBOM_STATUS: "PASS",
    DIGEST_STATUS: "PASS",
    COSIGN_STATUS: "PASS",
  },
  PRODUCTION_GATE: "PASS",
};

export const mockReleaseV1Blocked: ReleaseStatusV1 = {
  schema_version: 1,
  source_commit: "7c33671e9f2b4a1d8c6e5f3a2b1d0c9e8f7a6b5c",
  artifact_sha256:
    "8e4f1d2c3b4a59687766554433221100ffeeddccbbaa99887766554433221100",
  image_digest:
    "sha256:91f8c6b7a4d32e10c5f6b7a8d9e0123456789abcdef0123456789abcdef01230",
  controls: {
    GITLEAKS_STATUS: "PASS",
    DEPENDENCY_STATUS: "FAIL",
    UNIT_TEST_STATUS: "PASS",
    SBOM_STATUS: "PASS",
    DIGEST_STATUS: "PASS",
    COSIGN_STATUS: "PASS",
  },
  PRODUCTION_GATE: "BLOCKED",
};

// Aliases for backwards compatibility with M3 tests
export const mockReleasePass = mockReleaseV1Pass;
export const mockReleaseBlocked = mockReleaseV1Blocked;

// --- SCHEMA V2 FIXTURES (8 Controls, Registry, Deployment & Rollback) ---

export const mockReleaseV2Pass: ReleaseStatusV2 = {
  schema_version: 2,
  source_commit: "2222222222222222222222222222222222222222",
  artifact_sha256:
    "d486c1f919471029f75502e7525dff4fc0b0274a59f672f729ae95986afb5e7c",
  image_digest:
    "sha256:aa123c0fbf2e053c7643360532fb9f85957c44357f16af602e1a177c635a7fe0",
  registry: {
    image_reference: "ghcr.io/ueh-css-26c/order-app:v1.0.0",
    image_digest:
      "sha256:aa123c0fbf2e053c7643360532fb9f85957c44357f16af602e1a177c635a7fe0",
  },
  controls: {
    GITLEAKS_STATUS: "PASS",
    DEPENDENCY_STATUS: "PASS",
    UNIT_TEST_STATUS: "PASS",
    SBOM_STATUS: "PASS",
    DIGEST_STATUS: "PASS",
    COSIGN_STATUS: "PASS",
    VULNERABILITY_STATUS: "PASS",
    REGISTRY_STATUS: "PASS",
  },
  PRODUCTION_GATE: "PASS",
  deployment: {
    READINESS_STATUS: "PASS",
    API_STATUS: "PASS",
    DEPLOYMENT_GATE: "PASS",
    ROLLBACK_STATUS: "NOT_REQUIRED",
  },
};

// Explicit pre-deploy fixture: no deployment or scanner execution is implied.
export const mockReleaseV2PreDeploy: ReleaseStatusV2 = {
  ...mockReleaseV2Pass,
  deployment: {
    READINESS_STATUS: "NOT_RUN",
    API_STATUS: "NOT_RUN",
    DEPLOYMENT_GATE: "NOT_RUN",
    ROLLBACK_STATUS: "NOT_REQUIRED",
  },
};

export const mockReleaseV2Blocked: ReleaseStatusV2 = {
  schema_version: 2,
  source_commit: "2222222222222222222222222222222222222222",
  artifact_sha256:
    "d486c1f919471029f75502e7525dff4fc0b0274a59f672f729ae95986afb5e7c",
  image_digest:
    "sha256:aa123c0fbf2e053c7643360532fb9f85957c44357f16af602e1a177c635a7fe0",
  registry: {
    image_reference: "ghcr.io/ueh-css-26c/order-app:v1.0.0",
    image_digest:
      "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  },
  controls: {
    GITLEAKS_STATUS: "PASS",
    DEPENDENCY_STATUS: "PASS",
    UNIT_TEST_STATUS: "PASS",
    SBOM_STATUS: "PASS",
    DIGEST_STATUS: "PASS",
    COSIGN_STATUS: "PASS",
    VULNERABILITY_STATUS: "FAIL",
    REGISTRY_STATUS: "FAIL",
  },
  PRODUCTION_GATE: "BLOCKED",
  deployment: { ...mockReleaseV2PreDeploy.deployment },
};

export const mockReleaseV2Rollback: ReleaseStatusV2 = {
  schema_version: 2,
  source_commit: "2222222222222222222222222222222222222222",
  artifact_sha256:
    "d486c1f919471029f75502e7525dff4fc0b0274a59f672f729ae95986afb5e7c",
  image_digest:
    "sha256:aa123c0fbf2e053c7643360532fb9f85957c44357f16af602e1a177c635a7fe0",
  registry: {
    image_reference: "ghcr.io/ueh-css-26c/order-app:v1.0.0",
    image_digest:
      "sha256:aa123c0fbf2e053c7643360532fb9f85957c44357f16af602e1a177c635a7fe0",
  },
  controls: {
    GITLEAKS_STATUS: "PASS",
    DEPENDENCY_STATUS: "PASS",
    UNIT_TEST_STATUS: "PASS",
    SBOM_STATUS: "PASS",
    DIGEST_STATUS: "PASS",
    COSIGN_STATUS: "PASS",
    VULNERABILITY_STATUS: "PASS",
    REGISTRY_STATUS: "PASS",
  },
  PRODUCTION_GATE: "PASS",
  deployment: {
    READINESS_STATUS: "FAIL",
    API_STATUS: "FAIL",
    DEPLOYMENT_GATE: "FAIL",
    ROLLBACK_STATUS: "PASS",
  },
};

// Raw invalid/incomplete fixture
export const mockReleaseInvalid = {
  schema_version: 1,
  source_commit: "",
  artifact_sha256:
    "8e4f1d2c3b4a59687766554433221100ffeeddccbbaa99887766554433221100",
  image_digest:
    "sha256:91f8c6b7a4d32e10c5f6b7a8d9e0123456789abcdef0123456789abcdef01230",
  controls: {
    GITLEAKS_STATUS: "PASS",
    DEPENDENCY_STATUS: "PASS",
    UNIT_TEST_STATUS: "PASS",
    SBOM_STATUS: "PASS",
    DIGEST_STATUS: "PASS",
  },
  // Missing COSIGN_STATUS and PRODUCTION_GATE
} as unknown as ReleaseStatus;

export type ReleaseScenario =
  | "pass"
  | "blocked"
  | "v2-pass"
  | "v2-blocked"
  | "v2-rollback"
  | "invalid"
  | "error";

let currentScenario: ReleaseScenario = "v2-pass";

export function getReleaseScenario(): ReleaseScenario {
  return currentScenario;
}

export function setReleaseScenario(scenario: ReleaseScenario): void {
  currentScenario = scenario;
}
