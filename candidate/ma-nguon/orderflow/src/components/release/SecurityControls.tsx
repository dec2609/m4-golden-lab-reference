import type { ControlStatus, ReleaseControlsV1, ReleaseControlsV2 } from "../../types/release";
import ReleaseStatus from "./ReleaseStatus";

export interface SecurityControlsProps {
  controls?: ReleaseControlsV1 | ReleaseControlsV2 | Record<string, ControlStatus>;
}

const controlLabels: Record<string, { title: string; description: string }> = {
  GITLEAKS_STATUS: {
    title: "Gitleaks",
    description: "Secret detection & hardcoded credential prevention scan",
  },
  DEPENDENCY_STATUS: {
    title: "Dependency Policy",
    description: "Third-party dependency vulnerability & compliance verification",
  },
  UNIT_TEST_STATUS: {
    title: "Unit Tests",
    description: "Automated regression test suite execution",
  },
  SBOM_STATUS: {
    title: "Image SBOM",
    description: "Software Bill of Materials generated for container artifact",
  },
  DIGEST_STATUS: {
    title: "Artifact Digest",
    description: "Binary archive integrity checksum verification",
  },
  COSIGN_STATUS: {
    title: "Cosign",
    description: "Cryptographic supply chain signature verification",
  },
  VULNERABILITY_STATUS: {
    title: "Trivy Vulnerability Scan",
    description: "Container image vulnerability scanning for known CVEs",
  },
  REGISTRY_STATUS: {
    title: "Registry Verification",
    description: "Container image verification against authorized registry and digest",
  },
};

const v1ControlOrder = [
  "GITLEAKS_STATUS",
  "DEPENDENCY_STATUS",
  "UNIT_TEST_STATUS",
  "SBOM_STATUS",
  "DIGEST_STATUS",
  "COSIGN_STATUS",
];

const v2ControlOrder = [
  ...v1ControlOrder,
  "VULNERABILITY_STATUS",
  "REGISTRY_STATUS",
];

export default function SecurityControls({ controls }: SecurityControlsProps) {
  const ctrlMap = controls as Record<string, ControlStatus | undefined> | undefined;

  const isV2 = Boolean(
    ctrlMap &&
      ("VULNERABILITY_STATUS" in ctrlMap || "REGISTRY_STATUS" in ctrlMap)
  );

  const activeControlOrder = isV2 ? v2ControlOrder : v1ControlOrder;

  const passedCount = ctrlMap
    ? activeControlOrder.filter((k) => ctrlMap[k] === "PASS").length
    : 0;

  return (
    <section className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] shadow-xs">
      <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-[var(--text-card-title)] font-semibold text-[var(--text-primary)]">
              Security Controls Evaluation
            </h2>
            <span className="font-mono text-[10px] text-[var(--text-secondary)] bg-[var(--surface-subtle)] px-2 py-0.5 rounded border border-[var(--border)]">
              {isV2 ? "Schema v2 (8 Controls)" : "Schema v1 (6 Controls)"}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
            Automated verification stages required by the software release pipeline.
          </p>
        </div>
        <div className="text-right">
          <span className="font-mono text-xs font-semibold text-[var(--text-primary)]">
            {passedCount} / {activeControlOrder.length} Passed
          </span>
        </div>
      </div>

      <div className="divide-y divide-[var(--border-subtle)]">
        {activeControlOrder.map((key) => {
          const status = ctrlMap ? ctrlMap[key] : undefined;
          const info = controlLabels[key] || {
            title: key,
            description: "Pipeline security verification control",
          };

          return (
            <div
              key={key}
              className="flex items-center justify-between gap-4 px-5 py-3.5 hover:bg-[var(--surface-subtle)] transition-colors"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-[var(--text-primary)]">
                    {info.title}
                  </span>
                  <span className="font-mono text-[10px] text-[var(--text-muted)] bg-[var(--surface-subtle)] px-1.5 py-0.5 rounded border border-[var(--border-subtle)]">
                    {key}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-[var(--text-muted)] truncate">
                  {info.description}
                </p>
              </div>

              <div className="shrink-0">
                {status ? (
                  <ReleaseStatus status={status} />
                ) : (
                  <span className="font-mono text-xs font-semibold text-[var(--text-muted)] bg-[var(--surface-subtle)] px-2 py-1 rounded">
                    NOT FOUND
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
