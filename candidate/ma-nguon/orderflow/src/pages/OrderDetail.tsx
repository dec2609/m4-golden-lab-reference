import { useEffect, useState } from "react";
import { formatUtcOrderDate } from "../lib/orderPresentation";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Clock,
  Copy,
  Check,
  Package,
  User,
  ShieldCheck,
} from "lucide-react";
import PageHeader from "../components/layout/PageHeader";
import Button from "../components/ui/Button";
import Skeleton from "../components/ui/Skeleton";
import ErrorState from "../components/ui/ErrorState";
import OrderReleaseTrace from "../components/orders/OrderReleaseTrace";
import OrderStatus from "../components/orders/OrderStatus";
import { ordersService } from "../services/orders";
import type { Order } from "../types/order";
import OrdersSourceNotice, { useOrdersSource } from "../components/orders/OrdersSourceNotice";
import { useRequestScope } from "../lib/useRequestScope";

export default function OrderDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const { revision } = useOrdersSource();
  const scope = useRequestScope();
  const [loadedKey, setLoadedKey] = useState("");
  const viewKey = `${revision}:${id}`;

  useEffect(() => {
    const request = scope.start();
    async function loadOrder() {
      if (!id || !/^\d+$/.test(id) || !Number.isSafeInteger(Number(id)) || Number(id) <= 0) {
        setError("Invalid order ID specified.");
        setLoadedKey(viewKey);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      setOrder(null);
      try {
        const found = await ordersService.getOrderById(Number(id), { signal: request.signal });
        if (!request.isCurrent()) return;
        if (!found) {
          setError(`Order #${id} was not found in the operational store.`);
        } else {
          setOrder(found);
        }

      } catch {
        if (!request.isCurrent()) return;
        setError("Failed to retrieve order details from the server.");
      } finally {
        if (request.isCurrent()) { setLoadedKey(viewKey); setLoading(false); }
      }
    }

    loadOrder();
    return () => scope.cancel();
  }, [id, revision]);

  function handleCopyId() {
    if (!order) return;
    navigator.clipboard.writeText(String(order.id));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (loading || loadedKey !== viewKey) {
    return (
      <div className="space-y-6">
        <OrdersSourceNotice />
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-12 w-80" />
        <div className="grid gap-6 md:grid-cols-3">
          <Skeleton className="h-72 md:col-span-2 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="space-y-6">
        <OrdersSourceNotice />
        <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
          <Link
            to="/orders"
            className="inline-flex items-center gap-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            <ArrowLeft size={14} />
            <span>Orders</span>
          </Link>
        </div>
        <ErrorState
          title="Order Not Found"
          description={error || "Could not find the requested order."}
          action={
            <Button onClick={() => navigate("/orders")}>
              Back to Orders
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation */}
      <nav className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
        <Link
          to="/orders"
          className="inline-flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
        >
          <ArrowLeft size={13} />
          <span>Orders</span>
        </Link>
        <span>/</span>
        <span className="text-[var(--text-primary)] font-mono font-medium">#{order.id}</span>
      </nav>

      {/* Page Header */}
      <PageHeader
        title={`Order #${order.id}`}
        description={`Created on ${formatUtcOrderDate(order.created_at)}`}
        badge={<OrderStatus status={order.status} />}
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="md"
              onClick={handleCopyId}
              title="Copy Order ID"
            >
              {copied ? <Check size={14} className="text-[var(--success)]" /> : <Copy size={14} />}
              <span>{copied ? "Copied ID" : "Copy ID"}</span>
            </Button>
            <Button variant="secondary" onClick={() => navigate("/orders")}>
              Back to Orders
            </Button>
          </div>
        }
      />

      <OrdersSourceNotice />

      {/* 2-Column Operational Record Layout */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Column: Order Specifications */}
        <div className="space-y-6 lg:col-span-2">
          {/* Item Breakdown Card */}
          <section className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] shadow-xs overflow-hidden">
            <div className="flex items-center gap-2.5 border-b border-[var(--border)] px-5 py-3.5 bg-[var(--surface-subtle)]">
              <Package size={16} className="text-[var(--primary)]" />
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                Ordered Item Details
              </h2>
            </div>

            <div className="p-5 divide-y divide-[var(--border-subtle)]">
              <div className="py-3 first:pt-0 flex items-start justify-between gap-4">
                <div>
                  <span className="text-xs text-[var(--text-muted)] block">Product Name</span>
                  <span className="text-base font-semibold text-[var(--text-primary)] mt-0.5 block">
                    {order.product_name}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-xs text-[var(--text-muted)] block">Quantity</span>
                  <span className="font-mono text-base font-semibold text-[var(--text-primary)] mt-0.5 block">
                    {order.quantity} {order.quantity === 1 ? "unit" : "units"}
                  </span>
                </div>
              </div>

              <div className="pt-4 space-y-2">
                <span className="text-xs font-medium text-[var(--text-secondary)] block">
                  Processing Lifecycle Note
                </span>
                <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                  This order is registered in initial <strong className="text-[var(--text-secondary)] font-medium">pending</strong> state. It is queued for operational validation and downstream processing.
                </p>
              </div>
            </div>
          </section>

          {/* Operational Timeline & Record Metadata */}
          <section className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] shadow-xs p-5 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
              <Clock size={16} className="text-[var(--text-muted)]" />
              <span>Operational Timestamp & Records</span>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 text-xs">
              <div className="rounded-[var(--radius-control)] border border-[var(--border)] bg-[var(--surface-subtle)] p-3">
                <span className="text-[var(--text-muted)] block">Ingestion Timestamp</span>
                <span className="font-mono text-[var(--text-primary)] font-medium mt-1 block">
                  {order.created_at}
                </span>
              </div>

              <div className="rounded-[var(--radius-control)] border border-[var(--border)] bg-[var(--surface-subtle)] p-3">
                <span className="text-[var(--text-muted)] block">System Record Identifier</span>
                <span className="font-mono text-[var(--text-primary)] font-medium mt-1 block">
                  ORD-REC-{order.id}
                </span>
              </div>
            </div>
          </section>
        </div>

        {/* Secondary Column: Customer & System Trust Context */}
        <div className="space-y-6">
          {/* Customer Context */}
          <section className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] shadow-xs overflow-hidden">
            <div className="flex items-center gap-2.5 border-b border-[var(--border)] px-5 py-3.5 bg-[var(--surface-subtle)]">
              <User size={16} className="text-[var(--primary)]" />
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                Customer Context
              </h2>
            </div>

            <div className="p-5 space-y-3.5 text-xs">
              <div>
                <span className="text-[var(--text-muted)] block">Customer Name</span>
                <span className="font-semibold text-sm text-[var(--text-primary)] mt-0.5 block">
                  {order.customer_name}
                </span>
              </div>

              <div className="pt-2 border-t border-[var(--border-subtle)]">
                <span className="text-[var(--text-muted)] block">Ingestion Channel</span>
                <span className="text-[var(--text-secondary)] font-medium mt-0.5 block">
                  Internal Operations Gateway
                </span>
              </div>

              <div className="pt-2 border-t border-[var(--border-subtle)]">
                <span className="text-[var(--text-muted)] block">Data Validation State</span>
                <span className="inline-flex items-center gap-1 text-[var(--success)] font-medium mt-0.5">
                  <ShieldCheck size={13} />
                  Order fields validated by frontend
                </span>
              </div>
            </div>
          </section>

          <OrderReleaseTrace />
        </div>
      </div>
    </div>
  );
}
