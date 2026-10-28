import { useEffect, useState } from "react";
import { AlertCircle, AlertTriangle } from "lucide-react";
import PageHeader from "../components/layout/PageHeader";
import ReleaseOverview from "../components/release/ReleaseOverview";
import SecurityControls from "../components/release/SecurityControls";
import ArtifactIdentity from "../components/release/ArtifactIdentity";
import ReleaseDecision from "../components/release/ReleaseDecision";
import ErrorState from "../components/ui/ErrorState";
import Skeleton from "../components/ui/Skeleton";
import Button from "../components/ui/Button";
import type { ReleaseStatus } from "../types/release";
import { releaseService, type ReleaseScenario } from "../services/release";
import { useRequestScope } from "../lib/useRequestScope";
import { createHttpEvidenceSource, readEvidence, type EvidenceInspection } from "../services/releaseEvidence";

export default function ReleaseConsole() {
  const [release, setRelease] = useState<ReleaseStatus | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scenario, setScenario] = useState<ReleaseScenario>(releaseService.getScenario());
  const scope = useRequestScope();
  const configuredPath = import.meta.env.VITE_RELEASE_EVIDENCE_PATH || "";
  const [sourceMode, setSourceMode] = useState<"fixture" | "http">(configuredPath ? "http" : "fixture");
  const [pathInput, setPathInput] = useState(configuredPath);
  const [endpoint, setEndpoint] = useState(configuredPath);
  const [inspection, setInspection] = useState<EvidenceInspection | null>(null);

  async function loadRelease() {
    const request = scope.start();
    setLoading(true);
    setError(null);
    setValidationError(null);
    setRelease(null);
    setInspection(null);

    try {
      const source = sourceMode === "fixture"
        ? { description: "Development fixture: " + scenario, read: () => releaseService.getReleaseStatus() }
        : endpoint ? createHttpEvidenceSource(endpoint) : { description: "No evidence source configured", read: async () => null };
      const validation = await readEvidence(source, { signal: request.signal, fixture: sourceMode === "fixture" });
      if (!request.isCurrent()) return;
      setInspection(validation);

      if (validation.state !== "ready" || !validation.data) {
        setValidationError(validation.reason || "No valid release evidence is available.");
        setRelease(null);
      } else {
        setRelease(validation.data);
      }
    } catch (err: unknown) {
      if (!request.isCurrent()) return;
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to release verification service."
      );
    } finally {
      if (request.isCurrent()) setLoading(false);
    }
  }

  useEffect(() => {
    loadRelease();
    return () => scope.cancel();
  }, [scenario, sourceMode, endpoint]);

  function handleScenarioChange(newScenario: ReleaseScenario) {
    if (newScenario === scenario && sourceMode === "fixture") { void loadRelease(); return; }
    scope.cancel();
    setRelease(null);
    setLoading(true);
    releaseService.setScenario(newScenario);
    setSourceMode("fixture");
    setScenario(newScenario);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Release Console"
        description="Inspect supply chain security controls, release gates, and deployment status"
      />

      <form className="flex flex-wrap items-center gap-2 text-xs" onSubmit={(event) => {
        event.preventDefault(); scope.cancel(); setRelease(null); setLoading(true);
        if (sourceMode === "http" && endpoint === pathInput) { void loadRelease(); }
        else { setEndpoint(pathInput); setSourceMode("http"); }
      }}>
        <label htmlFor="release-source-path">Evidence JSON path (same origin)</label>
        <input id="release-source-path" className="border rounded px-2 py-1 bg-[var(--surface)]" value={pathInput} onChange={(event) => setPathInput(event.target.value)} placeholder="Producer path not configured" />
        <Button type="submit">Load evidence JSON</Button>
      </form>

      {/* Trust level is local consumer metadata, never copied from payload flags. */}
      <div className="flex items-center gap-2 rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface-subtle)] px-4 py-2.5 text-xs text-[var(--text-secondary)]">
        <span className="font-mono text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
          {sourceMode === "fixture" ? "[FIXTURE — DEMO / MOCK]" : "[UNVERIFIED EVIDENCE SOURCE]"}
        </span>
        <span>
          {sourceMode === "fixture"
            ? "Development fixture only; reported PASS values are not release evidence."
            : "Reported decisions only. HTTP/JSON/provenance consistency does not authenticate this source or approve a release. VERIFIED requires a trusted verifier that is not configured."}
          {inspection && <> Source: {inspection.source}. Provenance: {inspection.provenance}. Observed: {inspection.observedAt}.</>}
        </span>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="space-y-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-44 w-full" />
        </div>
      )}

      {/* Integration Error state */}
      {!loading && error && (
        <ErrorState
          title="Unable to load release data"
          description={error}
          action={<Button onClick={loadRelease}>Retry evidence load</Button>}
        />
      )}

      {/* Invalid / Incomplete Data state */}
      {!loading && !error && validationError && (
        <div className="space-y-6">
          <div className="rounded-[var(--radius-card)] border border-[var(--warning)]/30 bg-[var(--warning-soft)] p-5">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-[var(--warning)]" />
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-[var(--warning)]">
                  RELEASE DATA
                </p>
                <h3 className="mt-1 text-base font-semibold text-[var(--text-primary)]">
                  {inspection?.state === "empty" ? "NO RELEASE EVIDENCE" : "INVALID / INCOMPLETE"}
                </h3>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  The release payload cannot be parsed or lacks mandatory validation fields.
                </p>
                <div className="mt-3 rounded-[var(--radius-control)] bg-[var(--surface)] p-3 border border-[var(--border)] font-mono text-xs text-[var(--danger)]">
                  Validation details: {validationError}
                </div>
              </div>
            </div>
          </div>

          {/* Production Gate must be rendered as NOT AVAILABLE, NEVER as BLOCKED or PASS */}
          <ReleaseDecision status="NOT AVAILABLE" />

          <div className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] p-5 text-xs text-[var(--text-secondary)] space-y-2">
            <div className="flex items-center gap-2 font-medium text-[var(--text-primary)]">
              <AlertCircle size={15} className="text-[var(--text-muted)]" />
              <span>Security Guardrail Notice</span>
            </div>
            <p>
              Under OrderFlow boundary rules, the frontend never infers release outcomes. Missing or malformed data is strictly presented as &quot;NOT AVAILABLE&quot; to prevent masking upstream pipeline errors.
            </p>
          </div>
        </div>
      )}

      {!loading && error && <ReleaseDecision status="NOT AVAILABLE" />}

      {/* Valid Release Status state (PASS or BLOCKED strictly as reported) */}
      {!loading && !error && !validationError && release && (
        <div className="space-y-6">
          {/* 1. Release Overview */}
          <ReleaseOverview release={release} />

          {/* 2. Release Decisions: Production Gate + Deployment Gate + Rollback */}
          <ReleaseDecision
            status={release.PRODUCTION_GATE}
            showDeployment={release.schema_version === 2}
            deploymentGate={
              release.schema_version === 2
                ? release.deployment?.DEPLOYMENT_GATE
                : undefined
            }
            rollbackStatus={
              release.schema_version === 2
                ? release.deployment?.ROLLBACK_STATUS
                : undefined
            }
            deploymentDetails={
              release.schema_version === 2 && release.deployment
                ? {
                    readinessStatus: release.deployment.READINESS_STATUS,
                    apiStatus: release.deployment.API_STATUS,
                  }
                : undefined
            }
          />

          {/* 3. Security Controls */}
          <SecurityControls controls={release.controls} />

          {/* 4. Artifact Identity */}
          <ArtifactIdentity release={release} />
        </div>
      )}

      {/* Developer Sandbox Controls (visually secondary footer) */}
      <aside aria-label="Development fixture selector" className="mt-10 pt-4 border-t border-[var(--border)]/70 flex flex-wrap items-center justify-between gap-3 text-xs text-[var(--text-muted)]">
        <span className="font-mono text-[11px] uppercase tracking-wider text-[var(--text-muted)]">
          Development fixture scenario:
        </span>
        <div className="inline-flex flex-wrap items-center rounded-[var(--radius-control)] border border-[var(--border)] bg-[var(--surface-subtle)] p-0.5">
          <button
            type="button"
            onClick={() => handleScenarioChange("pass")}
            className={`rounded-[4px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
              scenario === "pass"
                ? "bg-[var(--surface)] text-[var(--success)] shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            1. V1 PASS
          </button>
          <button
            type="button"
            onClick={() => handleScenarioChange("blocked")}
            className={`rounded-[4px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
              scenario === "blocked"
                ? "bg-[var(--surface)] text-[var(--danger)] shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            2. V1 BLOCKED
          </button>
          <button
            type="button"
            onClick={() => handleScenarioChange("v2-pass")}
            className={`rounded-[4px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
              scenario === "v2-pass"
                ? "bg-[var(--surface)] text-[var(--success)] shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            3. V2 PASS (8 Controls)
          </button>
          <button
            type="button"
            onClick={() => handleScenarioChange("v2-blocked")}
            className={`rounded-[4px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
              scenario === "v2-blocked"
                ? "bg-[var(--surface)] text-[var(--danger)] shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            4. V2 BLOCKED (CVE/Reg)
          </button>
          <button
            type="button"
            onClick={() => handleScenarioChange("v2-rollback")}
            className={`rounded-[4px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
              scenario === "v2-rollback"
                ? "bg-[var(--surface)] text-[var(--warning)] shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            5. V2 ROLLBACK
          </button>
          <button
            type="button"
            onClick={() => handleScenarioChange("invalid")}
            className={`rounded-[4px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
              scenario === "invalid"
                ? "bg-[var(--surface)] text-[var(--warning)] shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            6. INVALID DATA
          </button>
          <button
            type="button"
            onClick={() => handleScenarioChange("error")}
            className={`rounded-[4px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
              scenario === "error"
                ? "bg-[var(--surface)] text-[var(--danger)] shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            7. Integration Error
          </button>
        </div>
      </aside>
    </div>
  );
}
