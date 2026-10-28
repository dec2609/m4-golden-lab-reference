import { useSyncExternalStore } from "react";
import { ordersService } from "../../services/orders";
import ReadinessNotice from "./ReadinessNotice";

export function useOrdersSource() {
  return useSyncExternalStore(ordersService.subscribe, ordersService.getSnapshot, ordersService.getSnapshot);
}

export default function OrdersSourceNotice() {
  const source = useOrdersSource();
  return (
    <div role="status" className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface-subtle)] px-4 py-2.5 text-xs text-[var(--text-secondary)]">
      <span className="font-mono font-semibold">
        {source.scenario === "live" ? "[LIVE MODE SELECTED]" : "[MOCK FIXTURE MODE]"}
      </span>{" "}
      {source.scenario === "live" ? (
        <span>API: {source.connection}. {source.detail} {source.observedAt && `Observed at ${source.observedAt}.`}<ReadinessNotice key={source.revision} revision={source.revision} /></span>
      ) : (
        <span>In-memory demo data ({source.scenario}); changes are not saved to PostgreSQL.</span>
      )}
    </div>
  );
}
