import { ShieldCheck, ShieldAlert, AlertTriangle, ArrowRightLeft, Server } from "lucide-react";
import type { DeploymentProbeStatus, DeploymentGateStatus, ProductionGateStatus, RollbackStatus } from "../../types/release";

export interface ReleaseDecisionProps {
  status: ProductionGateStatus | "NOT AVAILABLE";
  showDeployment?: boolean;
  deploymentGate?: DeploymentGateStatus;
  rollbackStatus?: RollbackStatus;
  deploymentDetails?: {
    readinessStatus?: DeploymentProbeStatus;
    apiStatus?: DeploymentProbeStatus;
  };
}

export default function ReleaseDecision({
  status,
  showDeployment = false,
  deploymentGate,
  rollbackStatus,
  deploymentDetails,
}: ReleaseDecisionProps) {
  return (
    <div className="space-y-3">
      <p className="text-xs text-[var(--text-secondary)]">Reported payload statuses only. Source authenticity and execution evidence are not verified by this view.</p>
      {/* 1. Production Gate Decision */}
      {status === "PASS" && (
        <section className="rounded-[var(--radius-card)] border border-[var(--success)]/30 bg-[var(--success-soft)] px-5 py-4 shadow-xs">
          <div className="flex items-start gap-3.5">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-[var(--success)]" />

            <div className="flex-1">
              <div className="flex items-center justify-between gap-3">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--success)]">
                  Gate 1: Production Gate Decision
                </span>
                <span className="inline-flex items-center rounded px-2 py-0.5 font-mono text-xs font-bold bg-[var(--success)] text-white">
                  PASS
                </span>
              </div>

              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                Payload reports Production Gate PASS.
              </p>

              <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                Mandatory controls report PASS; this display does not authorize deployment.
              </p>
            </div>
          </div>
        </section>
      )}

      {status === "BLOCKED" && (
        <section className="rounded-[var(--radius-card)] border border-[var(--danger)]/30 bg-[var(--danger-soft)] px-5 py-4 shadow-xs">
          <div className="flex items-start gap-3.5">
            <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-[var(--danger)]" />

            <div className="flex-1">
              <div className="flex items-center justify-between gap-3">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--danger)]">
                  Gate 1: Production Gate Decision
                </span>
                <span className="inline-flex items-center rounded px-2 py-0.5 font-mono text-xs font-bold bg-[var(--danger)] text-white">
                  BLOCKED
                </span>
              </div>

              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                Release blocked.
              </p>

              <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                Payload reports BLOCKED. This display does not perform artifact promotion.
              </p>
            </div>
          </div>
        </section>
      )}

      {status === "NOT AVAILABLE" && (
        <section className="rounded-[var(--radius-card)] border border-[var(--warning)]/30 bg-[var(--warning-soft)] px-5 py-4 shadow-xs">
          <div className="flex items-start gap-3.5">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-[var(--warning)]" />

            <div className="flex-1">
              <div className="flex items-center justify-between gap-3">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--warning)]">
                  Production Gate Decision
                </span>
                <span className="inline-flex items-center rounded px-2 py-0.5 font-mono text-xs font-bold bg-[var(--warning)] text-white">
                  NOT AVAILABLE
                </span>
              </div>

              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                Release data invalid or incomplete.
              </p>

              <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                No release approval can be inferred from the available data.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* 2. Deployment Gate Decision (Optional / Schema v2) */}
      {showDeployment && deploymentGate === undefined && (
        <section className="rounded-[var(--radius-card)] border border-[var(--border)] px-5 py-4 text-xs text-[var(--text-secondary)]">
          Deployment result: NOT AVAILABLE. No result was supplied; this is not interpreted as PASS, FAIL or proof that deployment ran.
        </section>
      )}
      {deploymentGate === "NOT_RUN" && (
        <section className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface-subtle)] px-5 py-4 text-xs text-[var(--text-secondary)]">
          <p className="font-mono font-semibold">Deployment Gate: NOT_RUN</p>
          <p className="mt-1">Not deployed / deployment checks not run. No deployment outcome or approval is available.</p>
          <p className="mt-1">Reported status only; this view does not verify execution or source authenticity.</p>
        </section>
      )}
      {(deploymentGate === "PASS" || deploymentGate === "FAIL") && (
        <section
          className={`rounded-[var(--radius-card)] border px-5 py-4 shadow-xs ${
            deploymentGate === "PASS"
              ? "border-[var(--success)]/30 bg-[var(--success-soft)]"
              : "border-[var(--danger)]/30 bg-[var(--danger-soft)]"
          }`}
        >
          <div className="flex items-start gap-3.5">
            <Server
              className={`mt-0.5 h-5 w-5 shrink-0 ${
                deploymentGate === "PASS" ? "text-[var(--success)]" : "text-[var(--danger)]"
              }`}
            />

            <div className="flex-1">
              <div className="flex items-center justify-between gap-3">
                <span
                  className={`text-[11px] font-bold uppercase tracking-wider ${
                    deploymentGate === "PASS" ? "text-[var(--success)]" : "text-[var(--danger)]"
                  }`}
                >
                  Gate 2: Deployment Gate Decision
                </span>
                <span
                  className={`inline-flex items-center rounded px-2 py-0.5 font-mono text-xs font-bold ${
                    deploymentGate === "PASS" ? "bg-[var(--success)] text-white" : "bg-[var(--danger)] text-white"
                  }`}
                >
                  {deploymentGate}
                </span>
              </div>

              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {deploymentGate === "PASS"
                  ? "Payload reports Deployment Gate PASS; active traffic is not verified here."
                  : "Payload reports Deployment Gate FAIL."}
              </p>

              <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-[var(--text-secondary)]">
                {deploymentDetails?.readinessStatus && (
                  <span>
                    Readiness probe:{" "}
                    <strong className="font-mono text-[var(--text-primary)]">
                      {deploymentDetails.readinessStatus}
                    </strong>
                  </span>
                )}
                {deploymentDetails?.apiStatus && (
                  <span>
                    API health:{" "}
                    <strong className="font-mono text-[var(--text-primary)]">
                      {deploymentDetails.apiStatus}
                    </strong>
                  </span>
                )}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* 3. Rollback State Banner (Optional / Schema v2) */}
      {rollbackStatus !== undefined && rollbackStatus !== "NOT_REQUIRED" && (
        <div
          className={`flex items-start gap-3 rounded-[var(--radius-card)] border p-4 text-xs ${
            rollbackStatus === "PASS"
              ? "border-[var(--warning)]/40 bg-[var(--warning-soft)] text-[var(--text-primary)]"
              : "border-[var(--danger)]/40 bg-[var(--danger-soft)] text-[var(--text-primary)]"
          }`}
        >
          <ArrowRightLeft
            className={`mt-0.5 h-4 w-4 shrink-0 ${
              rollbackStatus === "PASS" ? "text-[var(--warning)]" : "text-[var(--danger)]"
            }`}
          />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold uppercase tracking-wider">
                {rollbackStatus === "PASS"
                  ? "[ROLLBACK REPORTED PASS — RESTORATION UNVERIFIED]"
                  : "[ROLLBACK REPORTED FAIL]"}
              </span>
              <span className="font-mono text-[10px] bg-[var(--surface)] px-1.5 py-0.5 rounded border border-[var(--border)]">
                ROLLBACK_STATUS: {rollbackStatus}
              </span>
            </div>
            <p className="mt-1 text-[var(--text-secondary)]">
              {rollbackStatus === "PASS"
                ? "The payload reports rollback PASS. Execution, restored image identity and post-restore health require producer evidence; none is verified by this view."
                : "The payload reports rollback FAIL. Execution details require producer evidence."}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
