import { useState } from "react";
import { GitCommit, FileCheck2, Copy, Check, Globe } from "lucide-react";
import type { ReleaseStatus } from "../../types/release";

export interface ReleaseOverviewProps {
  release: ReleaseStatus;
}

export default function ReleaseOverview({ release }: ReleaseOverviewProps) {
  const [copiedCommit, setCopiedCommit] = useState(false);

  function handleCopyCommit() {
    navigator.clipboard.writeText(release.source_commit);
    setCopiedCommit(true);
    setTimeout(() => setCopiedCommit(false), 2000);
  }

  const isV2 = release.schema_version === 2;
  const registryRef = isV2 && release.registry?.image_reference ? release.registry.image_reference : null;

  return (
    <section className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] shadow-xs">
      <div className="border-b border-[var(--border)] px-5 py-4">
        <h2 className="text-[var(--text-card-title)] font-semibold text-[var(--text-primary)]">
          Release Overview
        </h2>
        <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
          Reported source commit and payload metadata; these fields do not identify the running build.
        </p>
      </div>

      <div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-3">
        <div className="flex items-start gap-3 rounded-[var(--radius-control)] border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-3.5">
          <GitCommit className="mt-0.5 h-4 w-4 shrink-0 text-[var(--primary)]" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-[var(--text-muted)] font-medium">Source Commit</span>
              <button
                type="button"
                onClick={handleCopyCommit}
                className="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--primary)] hover:text-[var(--primary-hover)] cursor-pointer"
              >
                {copiedCommit ? <Check size={12} className="text-[var(--success)]" /> : <Copy size={12} />}
                <span>{copiedCommit ? "Copied" : "Copy"}</span>
              </button>
            </div>
            <p className="mt-1 truncate font-mono text-xs font-semibold text-[var(--text-primary)] select-all" title={release.source_commit}>
              {release.source_commit}
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3 rounded-[var(--radius-control)] border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-3.5">
          <FileCheck2 className="mt-0.5 h-4 w-4 shrink-0 text-[var(--primary)]" />
          <div>
            <span className="text-xs text-[var(--text-muted)] font-medium">Payload Version</span>
            <p className="mt-1 font-mono text-xs font-semibold text-[var(--text-primary)]">
              v{release.schema_version} {isV2 ? "(8 Controls; producer contract pending)" : "(6 Controls)"}
            </p>
          </div>
        </div>

        {registryRef && (
          <div className="flex items-start gap-3 rounded-[var(--radius-control)] border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-3.5 sm:col-span-2 lg:col-span-1">
            <Globe className="mt-0.5 h-4 w-4 shrink-0 text-[var(--primary)]" />
            <div className="min-w-0 flex-1">
              <span className="text-xs text-[var(--text-muted)] font-medium">OCI Registry Target</span>
              <p className="mt-1 font-mono text-xs font-semibold text-[var(--text-primary)] truncate" title={registryRef}>
                {registryRef}
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
