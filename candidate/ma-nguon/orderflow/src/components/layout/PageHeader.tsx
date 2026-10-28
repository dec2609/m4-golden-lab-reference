import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  description?: string;
  badge?: ReactNode;
  breadcrumb?: ReactNode;
  action?: ReactNode;
}

export default function PageHeader({
  title,
  description,
  badge,
  breadcrumb,
  action,
}: PageHeaderProps) {
  return (
    <header className="space-y-1.5 pb-5 border-b border-[var(--border)]">
      {breadcrumb && (
        <div className="mb-2">
          {breadcrumb}
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="text-[20px] sm:text-[var(--text-page-title)] font-semibold tracking-tight text-[var(--text-primary)]">
              {title}
            </h1>
            {badge && <div className="shrink-0">{badge}</div>}
          </div>

          {description && (
            <p className="mt-1 text-xs sm:text-[13px] text-[var(--text-secondary)]">
              {description}
            </p>
          )}
        </div>

        {action && (
          <div className="shrink-0 flex items-center gap-2.5">
            {action}
          </div>
        )}
      </div>
    </header>
  );
}
