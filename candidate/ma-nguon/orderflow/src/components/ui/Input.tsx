import type { InputHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export default function Input({
  error = false,
  className,
  ...props
}: InputProps) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-[var(--radius-input)] border bg-[var(--surface)] px-3",
        "text-sm text-[var(--text-primary)]",
        "placeholder:text-[var(--text-muted)]",
        "transition-colors",
        "focus:border-[var(--primary)] focus:outline-none",
        "disabled:cursor-not-allowed disabled:bg-[var(--surface-subtle)]",
        error
          ? "border-[var(--danger)] focus:border-[var(--danger)]"
          : "border-[var(--border)]",
        className,
      )}
      {...props}
    />
  );
}

