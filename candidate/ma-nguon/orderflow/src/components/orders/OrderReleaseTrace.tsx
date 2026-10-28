import { Link } from "react-router-dom";

export default function OrderReleaseTrace() {
  return (
    <section className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] shadow-xs p-5 space-y-3.5">
      <p className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">Release Trace</p>
      <p className="text-xs text-[var(--text-secondary)]">
        NOT AVAILABLE: the order API does not provide release provenance. No release is attributed to this order.
      </p>
      <Link to="/release" className="text-xs font-semibold text-[var(--primary)]">View Release Console</Link>
    </section>
  );
}
