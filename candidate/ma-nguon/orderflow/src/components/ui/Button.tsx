import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

type ButtonVariant = "primary" | "secondary" | "destructive" | "ghost";
type ButtonSize = "sm" | "md";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[var(--radius-button)] font-medium cursor-pointer",
        "transition-all duration-[var(--duration-fast)]",
        "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--primary)]",
        "disabled:pointer-events-none disabled:opacity-50 select-none",

        size === "sm" && "h-8 px-2.5 text-xs",
        size === "md" && "h-9 px-3.5 text-[var(--text-button)]",

        variant === "primary" &&
          "bg-[var(--primary)] text-white shadow-xs hover:bg-[var(--primary-hover)] active:scale-[0.99]",

        variant === "secondary" &&
          "border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] shadow-xs hover:bg-[var(--surface-subtle)] hover:border-[var(--border-strong)] active:scale-[0.99]",

        variant === "destructive" &&
          "bg-[var(--danger)] text-white shadow-xs hover:bg-[var(--danger-hover)] active:scale-[0.99]",

        variant === "ghost" &&
          "text-[var(--text-secondary)] hover:bg-[var(--surface-subtle)] hover:text-[var(--text-primary)]",

        className,
      )}
      {...props}
    >
      {loading && (
        <span
          className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent shrink-0"
          aria-hidden="true"
        />
      )}

      {children}
    </button>
  );
}
