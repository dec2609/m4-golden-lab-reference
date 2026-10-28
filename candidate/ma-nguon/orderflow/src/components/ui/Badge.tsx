import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

export type BadgeVariant =
  | "neutral"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "brand";

export interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
  className?: string;
}

const variants: Record<BadgeVariant, string> = {
  neutral: "bg-[var(--surface-subtle)] text-[var(--text-secondary)] border border-[var(--border)]",
  success: "bg-[var(--success-soft)] text-[var(--success)] border border-[var(--success-border)]",
  warning: "bg-[var(--warning-soft)] text-[var(--warning)] border border-[var(--warning-border)]",
  danger: "bg-[var(--danger-soft)] text-[var(--danger)] border border-[var(--danger-border)]",
  info: "bg-[var(--info-soft)] text-[var(--info)] border border-[var(--info-border)]",
  brand: "bg-[var(--primary-soft)] text-[var(--primary)] border border-[var(--primary-border)]",
};

export default function Badge({
  variant = "neutral",
  children,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-[var(--radius-pill)]",
        "px-2.5 py-0.5 text-xs font-medium tracking-tight",
        variants[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
