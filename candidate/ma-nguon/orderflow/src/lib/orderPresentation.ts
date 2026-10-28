import type { Order } from "../types/order";
export function recentOrders(orders: Order[], limit = 5): Order[] {
  return [...orders].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at) || b.id - a.id).slice(0, limit);
}
export function formatUtcOrderDate(value: string): string {
  try {
    return new Intl.DateTimeFormat("en-US", { timeZone: "UTC", dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) + " UTC";
  } catch { return value; }
}
