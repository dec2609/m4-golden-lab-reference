import { cn } from "../../lib/utils";

export interface SkeletonProps {
  className?: string;
}

export default function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-[var(--radius-control)] bg-[var(--surface-subtle)]",
        className,
      )}
      aria-hidden="true"
    />
  );
}

