import { Search, X } from "lucide-react";
import Input from "../ui/Input";

export interface OrderSearchProps {
  value: string;
  onChange: (value: string) => void;
}

export default function OrderSearch({
  value,
  onChange,
}: OrderSearchProps) {
  return (
    <div className="relative w-full max-w-sm">
      <Search
        size={15}
        strokeWidth={2}
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]"
      />

      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Filter by Order ID, customer, product..."
        className="pl-9 pr-8 h-9 text-xs"
        aria-label="Filter orders"
      />

      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)] p-0.5 rounded cursor-pointer"
          aria-label="Clear filter"
        >
          <X size={13} />
        </button>
      )}
    </div>
  );
}
