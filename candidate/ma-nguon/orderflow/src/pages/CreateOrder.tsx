import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Plus } from "lucide-react";
import PageHeader from "../components/layout/PageHeader";
import Button from "../components/ui/Button";
import CreateOrderForm from "../components/orders/CreateOrderForm";
import OrderStatus from "../components/orders/OrderStatus";
import { ordersService } from "../services/orders";
import type { CreateOrderInput, Order } from "../types/order";
import OrdersSourceNotice, { useOrdersSource } from "../components/orders/OrdersSourceNotice";
import { useRequestScope } from "../lib/useRequestScope";

export default function CreateOrder() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [createdOrder, setCreatedOrder] = useState<Order | null>(null);
  const [simulateServerError, setSimulateServerError] = useState(false);

  const { scenario, revision } = useOrdersSource();
  const isLive = scenario === "live";
  const scope = useRequestScope();
  const submittingRef = useRef(false);
  const [createdRevision, setCreatedRevision] = useState(-1);
  useEffect(() => {
    scope.cancel();
    submittingRef.current = false;
    setSubmitting(false);
    setCreatedOrder(null);
  }, [revision]);

  async function handleCreateOrder(values: CreateOrderInput) {
    if (submittingRef.current) return;
    submittingRef.current = true;
    const request = scope.start();
    setSubmitting(true);
    try {
      if (simulateServerError) {
        // Simulate a client-side induced 500 error for UI testing
        await new Promise((resolve) => setTimeout(resolve, 400));
        throw new Error("Simulated client-side error; no request was sent to the backend.");
      }

      const order = await ordersService.createOrder(values, { signal: request.signal });
      if (!request.isCurrent()) return;
      setCreatedOrder(order);
      setCreatedRevision(revision);
    } finally {
      if (request.isCurrent()) { submittingRef.current = false; setSubmitting(false); }
    }
  }

  function handleReset() {
    setCreatedOrder(null);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
        <Link
          to="/orders"
          className="inline-flex items-center gap-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
        >
          <ArrowLeft size={14} />
          <span>Orders</span>
        </Link>
        <span>/</span>
        <span className="text-[var(--text-primary)]">New</span>
      </div>

      <PageHeader
        title="Create Order"
        description="Add a new customer order to the processing pipeline"
      />

      <OrdersSourceNotice />

      <div className="max-w-[540px]">
        {createdOrder && createdRevision === revision ? (
          /* Success state */
          <div className="rounded-[var(--radius-card)] border border-[var(--success)]/30 bg-[var(--surface)] p-6 space-y-5">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="h-6 w-6 text-[var(--success)] shrink-0 mt-0.5" />
              <div>
                <h2 className="text-base font-semibold text-[var(--text-primary)]">
                  Order Created Successfully
                </h2>
                <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                  Order #{createdOrder.id} was {isLive ? "acknowledged by the REST API" : "added to the in-memory mock store"} with status pending.
                </p>
              </div>
            </div>

            <div className="rounded-[var(--radius-control)] border border-[var(--border)] bg-[var(--surface-subtle)] p-4 space-y-2.5 text-xs">
              <div className="flex justify-between">
                <span className="text-[var(--text-muted)]">Order ID</span>
                <span className="font-mono font-medium text-[var(--text-primary)]">
                  #{createdOrder.id}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-muted)]">Customer</span>
                <span className="font-medium text-[var(--text-primary)]">
                  {createdOrder.customer_name}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-muted)]">Product</span>
                <span className="font-medium text-[var(--text-primary)]">
                  {createdOrder.product_name}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-muted)]">Quantity</span>
                <span className="font-medium text-[var(--text-primary)]">
                  {createdOrder.quantity}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[var(--text-muted)]">Status</span>
                <OrderStatus status={createdOrder.status} />
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-muted)]">Created At</span>
                <span className="font-mono text-[var(--text-secondary)]">
                  {createdOrder.created_at}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <Button variant="secondary" onClick={handleReset}>
                <Plus size={14} />
                <span>Create Another</span>
              </Button>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => navigate(`/orders/${createdOrder.id}`)}>
                  View Order
                </Button>
                <Button onClick={() => navigate("/orders")}>
                  Go to Orders
                </Button>
              </div>
            </div>
          </div>
        ) : (
          /* Form state */
          <div className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] p-6">
            <CreateOrderForm
              key={revision}
              onSubmit={handleCreateOrder}
              submitting={submitting}
              onCancel={() => navigate("/orders")}
            />
          </div>
        )}

        {/* Developer Sandbox Control (visually secondary) */}
        <aside aria-label="Development fixture selector" className="mt-8 pt-4 border-t border-[var(--border)]/70 flex items-center justify-between gap-3 text-xs text-[var(--text-muted)]">
          <span className="font-mono text-[11px] uppercase tracking-wider text-[var(--text-muted)]">
            Testing controls:
          </span>
          <button
            type="button"
            onClick={() => setSimulateServerError(!simulateServerError)}
            className={`rounded-[4px] border px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
              simulateServerError
                ? "border-[var(--danger)]/30 bg-[var(--danger-soft)] text-[var(--danger)]"
                : "border-[var(--border)] bg-[var(--surface-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            {simulateServerError ? "Simulating Client-side Error (500)" : "Normal operation"}
          </button>
        </aside>
      </div>
    </div>
  );
}
