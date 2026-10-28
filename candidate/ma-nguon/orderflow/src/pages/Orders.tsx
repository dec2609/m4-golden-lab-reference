import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, RefreshCw } from "lucide-react";
import PageHeader from "../components/layout/PageHeader";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Skeleton from "../components/ui/Skeleton";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import OrderTable from "../components/orders/OrderTable";
import OrderSearch from "../components/orders/OrderSearch";
import OrderFilters from "../components/orders/OrderFilters";
import { ordersService, type OrdersScenario } from "../services/orders";
import type { Order } from "../types/order";
import OrdersSourceNotice, { useOrdersSource } from "../components/orders/OrdersSourceNotice";
import { useRequestScope } from "../lib/useRequestScope";

export default function Orders() {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter & Search states
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "pending">("all");

  // Operational vs testing scenario state
  const { scenario, revision } = useOrdersSource();
  const scope = useRequestScope();
  const [loadedRevision, setLoadedRevision] = useState(-1);

  async function loadOrders() {
    const request = scope.start();
    setLoading(true);
    setError(null);
    setOrders([]);
    try {
      const data = await ordersService.getOrders({ signal: request.signal });
      if (!request.isCurrent()) return;
      setOrders(data);
    } catch (err: unknown) {
      if (!request.isCurrent()) return;
      const msg =
        err instanceof Error
          ? err.message
          : "The order service could not be reached (HTTP 500).";
      setError(msg);
    } finally {
      if (request.isCurrent()) { setLoadedRevision(revision); setLoading(false); }
    }
  }

  useEffect(() => {
    loadOrders();
    return () => scope.cancel();
  }, [revision]);

  function handleScenarioChange(newScenario: OrdersScenario) {
    ordersService.setScenario(newScenario);
  }

  // Filter orders by search and status
  const filteredOrders = useMemo(() => {
    return orders.filter((order) => {
      if (statusFilter !== "all" && order.status !== statusFilter) {
        return false;
      }

      if (searchQuery.trim()) {
        const query = searchQuery.trim().toLowerCase();
        const matchesId = String(order.id).includes(query);
        const matchesCustomer = order.customer_name.toLowerCase().includes(query);
        const matchesProduct = order.product_name.toLowerCase().includes(query);
        if (!matchesId && !matchesCustomer && !matchesProduct) {
          return false;
        }
      }

      return true;
    });
  }, [orders, searchQuery, statusFilter]);

  const isLoading = loading || loadedRevision !== revision;
  const isSearchActive = searchQuery.trim().length > 0 || statusFilter !== "all";
  const pendingCount = orders.filter((o) => o.status === "pending").length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Orders"
        description="Inspect, filter, and manage operational customer orders"
        badge={
          !isLoading && !error && orders.length > 0 ? (
            <Badge variant="brand">
              {orders.length} Total
            </Badge>
          ) : undefined
        }
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="md"
              onClick={loadOrders}
              disabled={isLoading}
              title="Refresh orders"
            >
              <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
              <span>Refresh</span>
            </Button>
            <Button onClick={() => navigate("/orders/new")}>
              <Plus size={15} />
              <span>Create Order</span>
            </Button>
          </div>
        }
      />

      <OrdersSourceNotice />

      {/* Filter and Search Toolbar */}
      {!isLoading && !error && orders.length > 0 && (
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <OrderSearch value={searchQuery} onChange={setSearchQuery} />
          <div className="flex items-center justify-between sm:justify-end gap-3">
            <span className="text-xs text-[var(--text-muted)] font-mono">
              Showing {filteredOrders.length} of {orders.length}
            </span>
            <OrderFilters
              status={statusFilter}
              onStatusChange={setStatusFilter}
              pendingCount={pendingCount}
            />
          </div>
        </div>
      )}

      {/* States Presentation */}
      {isLoading ? (
        <div className="space-y-3">
          <div className="flex justify-between gap-4">
            <Skeleton className="h-9 w-64" />
            <Skeleton className="h-9 w-24" />
          </div>
          <div className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] p-6 space-y-4">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        </div>
      ) : error ? (
        <ErrorState
          title="Unable to load orders"
          description={error}
          action={<Button onClick={loadOrders}>Try again</Button>}
        />
      ) : orders.length === 0 ? (
        /* Empty Database State */
        <div className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] shadow-xs">
          <EmptyState
            title="No orders yet"
            description="Create your first customer order to start operational processing."
            action={
              <Button onClick={() => navigate("/orders/new")}>
                <Plus size={15} />
                <span>Create Order</span>
              </Button>
            }
          />
        </div>
      ) : filteredOrders.length === 0 && isSearchActive ? (
        /* Search/Filter Empty State */
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <OrderSearch value={searchQuery} onChange={setSearchQuery} />
            <OrderFilters
              status={statusFilter}
              onStatusChange={setStatusFilter}
              pendingCount={pendingCount}
            />
          </div>
          <div className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] shadow-xs">
            <EmptyState
              title="No orders match your filter"
              description="No active orders match the current search term or status filter."
              action={
                <Button
                  variant="secondary"
                  onClick={() => {
                    setSearchQuery("");
                    setStatusFilter("all");
                  }}
                >
                  Clear all filters
                </Button>
              }
            />
          </div>
        </div>
      ) : (
        /* Populated Orders Table */
        <OrderTable
          orders={filteredOrders}
          onOrderClick={(order) => navigate(`/orders/${order.id}`)}
        />
      )}

      {/* Developer Sandbox Controls */}
      <aside aria-label="Development fixture selector" className="mt-12 pt-4 border-t border-[var(--border)] flex flex-wrap items-center justify-between gap-3 text-xs text-[var(--text-muted)]">
        <span className="font-mono text-[11px] uppercase tracking-wider text-[var(--text-muted)]">
          Data source scenario:
        </span>
        <div className="inline-flex items-center rounded-[var(--radius-control)] border border-[var(--border)] bg-[var(--surface-subtle)] p-0.5">
          <button
            type="button"
            onClick={() => handleScenarioChange("live")}
            className={`rounded-[4px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
              scenario === "live"
                ? "bg-[var(--surface)] text-[var(--success)] shadow-xs font-semibold"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            Live API
          </button>
          <button
            type="button"
            onClick={() => handleScenarioChange("populated")}
            className={`rounded-[4px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
              scenario === "populated"
                ? "bg-[var(--surface)] text-[var(--text-primary)] shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            Mock Populated
          </button>
          <button
            type="button"
            onClick={() => handleScenarioChange("empty")}
            className={`rounded-[4px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
              scenario === "empty"
                ? "bg-[var(--surface)] text-[var(--text-primary)] shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            Mock Empty
          </button>
          <button
            type="button"
            onClick={() => handleScenarioChange("error")}
            className={`rounded-[4px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
              scenario === "error"
                ? "bg-[var(--surface)] text-[var(--danger)] shadow-xs"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            Mock Error
          </button>
        </div>
      </aside>
    </div>
  );
}
