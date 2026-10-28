import { useState } from "react";
import { Fingerprint, Package, Copy, Check, Server } from "lucide-react";
import type { ReleaseStatus } from "../../types/release";

export interface ArtifactIdentityProps {
  release: ReleaseStatus;
}

export default function ArtifactIdentity({ release }: ArtifactIdentityProps) {
  const [copiedSha, setCopiedSha] = useState(false);
  const [copiedDigest, setCopiedDigest] = useState(false);
  const [copiedRegistryDigest, setCopiedRegistryDigest] = useState(false);

  function copyText(text: string, type: "sha" | "digest" | "regDigest") {
    navigator.clipboard.writeText(text);
    if (type === "sha") {
      setCopiedSha(true);
      setTimeout(() => setCopiedSha(false), 2000);
    } else if (type === "digest") {
      setCopiedDigest(true);
      setTimeout(() => setCopiedDigest(false), 2000);
    } else {
      setCopiedRegistryDigest(true);
      setTimeout(() => setCopiedRegistryDigest(false), 2000);
    }
  }

  const isV2 = release.schema_version === 2;
  const registryDigest = isV2 && release.registry?.image_digest ? release.registry.image_digest : null;

  return (
    <section className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] shadow-xs">
      <div className="border-b border-[var(--border)] px-5 py-4">
        <h2 className="text-[var(--text-card-title)] font-semibold text-[var(--text-primary)]">
          Artifact Identity
        </h2>
        <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
          Identifiers reported in the payload; provenance and digest kind require producer confirmation.
        </p>
      </div>

      <div className="divide-y divide-[var(--border-subtle)]">
        {/* OCI Archive SHA-256 */}
        <div className="flex items-start gap-3 px-5 py-4">
          <Package className="mt-0.5 h-4 w-4 shrink-0 text-[var(--text-muted)]" />

          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-[var(--text-primary)]">
                Archive SHA-256 (reported)
              </span>
              <button
                type="button"
                onClick={() => copyText(release.artifact_sha256, "sha")}
                className="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--primary)] hover:text-[var(--primary-hover)] cursor-pointer"
              >
                {copiedSha ? <Check size={12} className="text-[var(--success)]" /> : <Copy size={12} />}
                <span>{copiedSha ? "Copied" : "Copy"}</span>
              </button>
            </div>
            <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
              Reported archive checksum; this view does not hash the artifact
            </p>
            <p className="mt-2 break-all font-mono text-xs leading-5 text-[var(--text-primary)] select-all bg-[var(--surface-subtle)] px-3 py-2 rounded-[var(--radius-control)] border border-[var(--border)]">
              {release.artifact_sha256}
            </p>
          </div>
        </div>

        {/* Image Manifest Digest */}
        <div className="flex items-start gap-3 px-5 py-4">
          <Fingerprint className="mt-0.5 h-4 w-4 shrink-0 text-[var(--text-muted)]" />

          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-[var(--text-primary)]">
                Image Digest (reported)
              </span>
              <button
                type="button"
                onClick={() => copyText(release.image_digest, "digest")}
                className="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--primary)] hover:text-[var(--primary-hover)] cursor-pointer"
              >
                {copiedDigest ? <Check size={12} className="text-[var(--success)]" /> : <Copy size={12} />}
                <span>{copiedDigest ? "Copied" : "Copy"}</span>
              </button>
            </div>
            <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
              Index versus platform manifest identity is not established by this view
            </p>
            <p className="mt-2 break-all font-mono text-xs leading-5 text-[var(--text-primary)] select-all bg-[var(--surface-subtle)] px-3 py-2 rounded-[var(--radius-control)] border border-[var(--border)]">
              {release.image_digest}
            </p>
          </div>
        </div>

        {/* Registry Image Digest (if present in Schema v2) */}
        {registryDigest && (
          <div className="flex items-start gap-3 px-5 py-4">
            <Server className="mt-0.5 h-4 w-4 shrink-0 text-[var(--text-muted)]" />

            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-[var(--text-primary)]">
                    Registry Image Digest
                  </span>
                  {registryDigest === release.image_digest ? (
                    <span className="font-mono text-[10px] font-semibold text-[var(--success)] bg-[var(--success-soft)] px-2 py-0.5 rounded border border-[var(--success)]/30">
                      EQUAL IN PAYLOAD
                    </span>
                  ) : (
                    <span className="font-mono text-[10px] font-semibold text-[var(--danger)] bg-[var(--danger-soft)] px-2 py-0.5 rounded border border-[var(--danger)]/30">
                      MISMATCH
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => copyText(registryDigest, "regDigest")}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--primary)] hover:text-[var(--primary-hover)] cursor-pointer"
                >
                  {copiedRegistryDigest ? <Check size={12} className="text-[var(--success)]" /> : <Copy size={12} />}
                  <span>{copiedRegistryDigest ? "Copied" : "Copy"}</span>
                </button>
              </div>
              <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
                {registryDigest === release.image_digest
                  ? "Payload digests are equal. No registry query or authenticity verification was performed by this view."
                  : "Payload digests differ. This view does not query the registry."}
              </p>
              <p className="mt-2 break-all font-mono text-xs leading-5 text-[var(--text-primary)] select-all bg-[var(--surface-subtle)] px-3 py-2 rounded-[var(--radius-control)] border border-[var(--border)]">
                {registryDigest}
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
