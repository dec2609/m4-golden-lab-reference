export type ControlStatus = "PASS" | "FAIL";
export type ProductionGateStatus = "PASS" | "BLOCKED";
export type DeploymentProbeStatus = "PASS" | "FAIL" | "NOT_RUN";
export type DeploymentGateStatus = "PASS" | "FAIL" | "NOT_RUN";
export type RollbackStatus = "PASS" | "FAIL" | "NOT_REQUIRED";

export type ReleaseControlKeyV1 =
  | "GITLEAKS_STATUS"
  | "DEPENDENCY_STATUS"
  | "UNIT_TEST_STATUS"
  | "SBOM_STATUS"
  | "DIGEST_STATUS"
  | "COSIGN_STATUS";

export type ReleaseControlKeyV2 =
  | ReleaseControlKeyV1
  | "VULNERABILITY_STATUS"
  | "REGISTRY_STATUS";

export type ReleaseControlsV1 = Record<ReleaseControlKeyV1, ControlStatus>;
export type ReleaseControlsV2 = Record<ReleaseControlKeyV2, ControlStatus>;

export interface ReleaseStatusV1 {
  schema_version: 1;
  source_commit: string;
  artifact_sha256: string;
  image_digest: string;
  controls: ReleaseControlsV1;
  PRODUCTION_GATE: ProductionGateStatus;
}

export interface ReleaseStatusV2 {
  schema_version: 2;
  source_commit: string;
  artifact_sha256: string;
  image_digest: string;
  registry: {
    image_reference: string;
    image_digest: string;
  };
  controls: ReleaseControlsV2;
  PRODUCTION_GATE: ProductionGateStatus;
  deployment: {
    READINESS_STATUS: DeploymentProbeStatus;
    API_STATUS: DeploymentProbeStatus;
    DEPLOYMENT_GATE: DeploymentGateStatus;
    ROLLBACK_STATUS: RollbackStatus;
  };
}

export type ReleaseStatus = ReleaseStatusV1 | ReleaseStatusV2;
