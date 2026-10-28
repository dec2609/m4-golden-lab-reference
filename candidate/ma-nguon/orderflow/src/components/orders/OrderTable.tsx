import { ArrowUpRight } from "lucide-react";
import { formatUtcOrderDate } from "../../lib/orderPresentation";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/Table";
import OrderStatus from "./OrderStatus";
import type { Order } from "../../types/order";

export interface OrderTableProps {
  orders: Order[];
  onOrderClick?: (order: Order) => void;
}

export default function OrderTable({
  orders,
  onOrderClick,
}: OrderTableProps) {
  return (
    <div className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] shadow-xs overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-28">Order ID</TableHead>
            <TableHead>Customer</TableHead>
            <TableHead>Product</TableHead>
            <TableHead className="w-24 text-right">Quantity</TableHead>
            <TableHead className="w-32">Status</TableHead>
            <TableHead className="w-48">Timestamp (UTC)</TableHead>
            <TableHead className="w-12 text-center" aria-label="Action" />
          </TableRow>
        </TableHeader>

        <TableBody>
          {orders.map((order) => (
            <TableRow
              key={order.id}
              className={onOrderClick ? "group cursor-pointer hover:bg-[var(--surface-hover)]" : undefined}
              onClick={() => onOrderClick?.(order)}
              tabIndex={onOrderClick ? 0 : undefined}
              aria-label={onOrderClick ? `Open order ${order.id}` : undefined}
              onKeyDown={(event) => { if (onOrderClick && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); onOrderClick(order); } }}
            >
              <TableCell className="font-mono text-xs font-semibold text-[var(--primary)] group-hover:underline">
                #{order.id}
              </TableCell>

              <TableCell className="font-medium text-[var(--text-primary)]">
                {order.customer_name}
              </TableCell>

              <TableCell className="text-[var(--text-secondary)]">
                {order.product_name}
              </TableCell>

              <TableCell className="text-right font-medium text-[var(--text-primary)] font-mono text-xs">
                {order.quantity}
              </TableCell>

              <TableCell>
                <OrderStatus status={order.status} />
              </TableCell>

              <TableCell className="text-[var(--text-secondary)] font-mono text-xs">
                {formatUtcOrderDate(order.created_at)}
              </TableCell>

              <TableCell className="text-center">
                <ArrowUpRight
                  size={14}
                  className="inline-block text-[var(--text-muted)] opacity-0 group-hover:opacity-100 group-hover:text-[var(--primary)] transition-all"
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
