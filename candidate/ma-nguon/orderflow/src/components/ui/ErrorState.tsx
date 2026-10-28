import { AlertCircle } from "lucide-react";
import type { ReactNode } from "react";

export interface ErrorStateProps {
  title?: string;
  description?: string;
  action?: ReactNode;
}

export default function ErrorState({
  title = "Something went wrong",
  description = "We couldn't load this information. Please try again.",
  action,
}: ErrorStateProps) {
  return (
    <div className="flex min-h-56 flex-col items-center justify-center px-6 py-10 text-center">
      <AlertCircle
        size={20}
        className="text-[var(--danger)]"
        strokeWidth={1.8}
      />

      <h2 className="mt-3 text-sm font-semibold text-[var(--text-primary)]">
        {title}
      </h2>

      <p className="mt-1 max-w-sm text-sm text-[var(--text-secondary)]">
        {description}
      </p>

      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

