import { useEffect, useState } from "react";
import { checkReadiness, type ReadinessObservation } from "../../services/readiness";
import { useRequestScope } from "../../lib/useRequestScope";

export function ReadinessView({ observation }: { observation: ReadinessObservation }) {
  return <span>Database readiness: {observation.state}. {observation.origin === "SIMULATED" ? "SIMULATED test double; no database verification." : "Observed /ready HTTP response at " + observation.observedAt + "."}</span>;
}
export default function ReadinessNotice({ revision }: { revision: number }) {
  const [result, setResult] = useState<ReadinessObservation | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState(false);
  const scope = useRequestScope();
  useEffect(() => {
    scope.cancel(); setResult(null); setError(false); setChecking(false);
    return () => scope.cancel();
  }, [revision]);
  async function check() {
    const request = scope.start();
    setChecking(true); setResult(null); setError(false);
    try {
      const observed = await checkReadiness({ signal: request.signal });
      if (request.isCurrent()) setResult(observed);
    } catch {
      if (request.isCurrent()) setError(true);
    } finally {
      if (request.isCurrent()) setChecking(false);
    }
  }
  return <span className="block mt-1">
    {checking ? "Database readiness: CHECKING." : result ? <ReadinessView observation={result} /> : error ? "Database readiness: ERROR / NOT CONFIRMED." : "Database readiness: NOT CHECKED."}
    {" "}<button type="button" className="underline" disabled={checking} onClick={check}>Check readiness</button>
  </span>;
}
