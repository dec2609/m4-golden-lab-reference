import Badge from "../ui/Badge";
import type { OrderStatus as OrderStatusType } from "../../types/order";

export interface OrderStatusProps {
  status: OrderStatusType;
}

const config: Record<OrderStatusType, { label: string; variant: "neutral" | "info" | "success" | "danger" }> = {
  pending: {
    label: "Pending",
    variant: "neutral",
  },
  confirmed: {
    label: "Confirmed",
    variant: "info",
  },
  shipped: {
    label: "Shipped",
    variant: "success",
  },
  cancelled: {
    label: "Cancelled",
    variant: "danger",
  },
};

export default function OrderStatus({ status }: OrderStatusProps) {
  const current = config[status] || {
    label: status,
    variant: "neutral" as const,
  };

  return <Badge variant={current.variant}>{current.label}</Badge>;
}
