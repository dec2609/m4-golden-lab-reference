import { CheckCircle2, CircleAlert } from "lucide-react";
import Badge from "../ui/Badge";

export interface ReleaseStatusProps {
  status: "PASS" | "FAIL" | "BLOCKED";
}

export default function ReleaseStatus({ status }: ReleaseStatusProps) {
  if (status === "PASS") {
    return (
      <span className="inline-flex items-center gap-1.5">
        <CheckCircle2 className="h-4 w-4 text-[var(--success)]" />
        <Badge variant="success">PASS</Badge>
      </span>
    );
  }

  if (status === "FAIL") {
    return (
      <span className="inline-flex items-center gap-1.5">
        <CircleAlert className="h-4 w-4 text-[var(--danger)]" />
        <Badge variant="danger">FAIL</Badge>
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5">
      <CircleAlert className="h-4 w-4 text-[var(--danger)]" />
      <Badge variant="danger">BLOCKED</Badge>
    </span>
  );
}

