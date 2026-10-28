import { useEffect, useState } from "react";
import { recentOrders as selectRecentOrders, formatUtcOrderDate } from "../lib/orderPresentation";
import { Link, useNavigate } from "react-router-dom";
import {
  Plus,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  GitCommit,
  RefreshCw,
  Package,
  Layers,
  ArrowUpRight,
} from "lucide-react";
import PageHeader from "../components/layout/PageHeader";
import Button from "../components/ui/Button";
import Skeleton from "../components/ui/Skeleton";
import ErrorState from "../components/ui/ErrorState";
import OrderStatus from "../components/orders/OrderStatus";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/Table";
import { ordersService } from "../services/orders";
import { releaseService } from "../services/release";
import type { Order } from "../types/order";
import type { ReleaseStatus } from "../types/release";
import OrdersSourceNotice, { useOrdersSource } from "../components/orders/OrdersSourceNotice";
import { useRequestScope } from "../lib/useRequestScope";

export default function Dashboard() {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<Order[]>([]);
  const [release, setRelease] = useState<ReleaseStatus | null>(null);
  const [isReleaseValid, setIsReleaseValid] = useState<boolean>(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { revision } = useOrdersSource();
  const scope = useRequestScope();
  const [loadedRevision, setLoadedRevision] = useState(-1);

  async function loadData() {
    const request = scope.start();
    setLoading(true);
    setError(null);
    setOrders([]);
    setRelease(null);
    setIsReleaseValid(false);
    try {
      const [fetchedOrders, rawRelease] = await Promise.all([
        ordersService.getOrders({ signal: request.signal }),
        releaseService.getReleaseStatus(),
      ]);

      if (!request.isCurrent()) return;
      setOrders(fetchedOrders);

      const validation = releaseService.validateRelease(rawRelease);
      if (validation.isValid && validation.data) {
        setRelease(validation.data);
        setIsReleaseValid(true);
      } else {
        setIsReleaseValid(false);
        setRelease(null);
      }
    } catch {
      if (!request.isCurrent()) return;
      setError("Unable to connect to OrderFlow operational services.");
    } finally {
      if (request.isCurrent()) { setLoadedRevision(revision); setLoading(false); }
    }
  }

  useEffect(() => {
    loadData();
    return () => scope.cancel();
  }, [revision]);

  if (loading || loadedRevision !== revision) {
    return (
      <div className="space-y-6">
        <OrdersSourceNotice />
        <PageHeader
          title="Operations Home"
          description="Operational overview of incoming orders and software release verification"
          action={<Skeleton className="h-9 w-32" />}
        />
        <Skeleton className="h-16 w-full" />
        <div className="grid gap-4 sm:grid-cols-3">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <OrdersSourceNotice />
        <PageHeader
          title="Operations Home"
          description="Operational overview of incoming orders and software release verification"
        />
        <ErrorState
          title="Operational Service Unavailable"
          description={error}
          action={<Button onClick={loadData}>Retry Connection</Button>}
        />
      </div>
    );
  }

  const recentOrders = selectRecentOrders(orders);
  const totalOrders = orders.length;
  const pendingOrders = orders.filter((o) => o.status === "pending").length;

  const passedControlsCount = release?.controls
    ? Object.values(release.controls).filter((c) => c === "PASS").length
    : 0;
  const totalControlsCount = release?.controls
    ? Object.keys(release.controls).length
    : 0;

  return (
    <div className="space-y-7">
      {/* Page Header */}
      <PageHeader
        title="Operations Home"
        description="Real-time order queue, operational attention, and software release trust"
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={loadData}
              title="Refresh status"
            >
              <RefreshCw size={14} />
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

      {/* Attention / Exceptions Layer */}
      {!isReleaseValid ? (
        <div className="rounded-[var(--radius-card)] border border-[var(--warning-border)] bg-[var(--warning-soft)] p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 shadow-xs">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-[var(--warning)] shrink-0 mt-0.5" />
            <div>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                Operational Warning: Release Data Incomplete
              </h2>
              <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                Current release payload failed schema verification. Production Gate cannot be validated (State: <span className="font-semibold text-[var(--warning)]">NOT AVAILABLE</span>).
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => navigate("/release")}
            className="shrink-0 self-start sm:self-center"
          >
            <span>Inspect Release</span>
            <ArrowRight size={13} />
          </Button>
        </div>
      ) : release?.PRODUCTION_GATE === "BLOCKED" ? (
        <div className="rounded-[var(--radius-card)] border border-[var(--danger-border)] bg-[var(--danger-soft)] p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 shadow-xs">
          <div className="flex items-start gap-3">
            <ShieldAlert className="h-5 w-5 text-[var(--danger)] shrink-0 mt-0.5" />
            <div>
              <h2 className="text-sm font-semibold text-[var(--danger)]">
                Demo fixture: Release Gate BLOCKED
              </h2>
              <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                This demo payload reports a blocked release. No live pipeline evidence is connected.
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="destructive"
            onClick={() => navigate("/release")}
            className="shrink-0 self-start sm:self-center"
          >
            <span>Review Failed Controls</span>
            <ArrowRight size={13} />
          </Button>
        </div>
      ) : (
        <div className="rounded-[var(--radius-card)] border border-[var(--success-border)] bg-[var(--success-soft)] px-4 py-3 flex items-center justify-between text-xs text-[var(--text-secondary)] shadow-xs">
          <div className="flex items-center gap-2.5">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--success)] opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--success)]" />
            </span>
            <span className="font-medium text-[var(--success)]">
              Demo release fixture reports PASS
            </span>
            <span className="hidden sm:inline text-[var(--text-muted)]">—</span>
            <span className="hidden sm:inline text-[var(--text-muted)]">
              Demo fixture reports {passedControlsCount}/{totalControlsCount} controls passed; release evidence is not connected.
            </span>
          </div>
          <Link
            to="/release"
            className="text-xs font-semibold text-[var(--primary)] hover:underline inline-flex items-center gap-1"
          >
            <span>Release Console</span>
            <ArrowRight size={12} />
          </Link>
        </div>
      )}

      {/* Core Operational Overview Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Total Orders Card */}
        <div className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">
              Total Order Pipeline
            </span>
            <Package size={16} className="text-[var(--text-muted)]" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-semibold text-[var(--text-primary)]">
              {totalOrders}
            </span>
            <span className="text-xs text-[var(--text-muted)]">records</span>
          </div>
          <p className="mt-2 text-xs text-[var(--text-secondary)]">
            Active operational orders registered in the system
          </p>
        </div>

        {/* Pending Orders Card */}
        <div className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">
              Pending Queue
            </span>
            <Layers size={16} className="text-[var(--text-muted)]" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-semibold text-[var(--text-primary)]">
              {pendingOrders}
            </span>
            <span className="text-xs text-[var(--text-muted)]">
              {totalOrders > 0 ? `(${Math.round((pendingOrders / totalOrders) * 100)}% of queue)` : "0%"}
            </span>
          </div>
          <p className="mt-2 text-xs text-[var(--text-secondary)]">
            Orders currently awaiting fulfillment and dispatch
          </p>
        </div>

        {/* System Trust & Release Gate Card */}
        <div className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                System Trust Gate
              </span>
              <span className="font-mono text-[10px] text-[var(--text-muted)] uppercase">
                UI Fixture
              </span>
            </div>
            <div className="mt-3 flex items-center gap-2">
              {!isReleaseValid ? (
                <span className="inline-flex items-center gap-1.5 text-base font-semibold text-[var(--warning)]">
                  <AlertTriangle size={18} />
                  NOT AVAILABLE
                </span>
              ) : release?.PRODUCTION_GATE === "PASS" ? (
                <span className="inline-flex items-center gap-1.5 text-base font-semibold text-[var(--success)]">
                  <ShieldCheck size={18} />
                  PASS
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-base font-semibold text-[var(--danger)]">
                  <ShieldAlert size={18} />
                  BLOCKED
                </span>
              )}
            </div>
            <p className="mt-2 text-xs text-[var(--text-secondary)]">
              {isReleaseValid && release
                ? `${passedControlsCount} of ${totalControlsCount} fixture controls report PASS`
                : "Schema validation failure"}
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-[var(--border-subtle)] flex items-center justify-between text-xs">
            <span className="text-[var(--text-muted)] font-mono text-[11px]">
              {release ? `Commit ${release.source_commit.substring(0, 8)}` : "No commit"}
            </span>
            <Link
              to="/release"
              className="font-semibold text-[var(--primary)] hover:underline inline-flex items-center gap-1"
            >
              <span>Inspect Gate</span>
              <ArrowRight size={11} />
            </Link>
          </div>
        </div>
      </div>

      {/* Recent Orders Section */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              Recent Operational Orders
            </h2>
            <p className="text-xs text-[var(--text-secondary)]">
              Latest transactions registered in the processing pipeline
            </p>
          </div>
          <Link
            to="/orders"
            className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] transition-colors"
          >
            <span>View full order list ({totalOrders})</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        <div className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] shadow-xs overflow-hidden">
          {recentOrders.length === 0 ? (
            <div className="p-8 text-center text-xs text-[var(--text-secondary)]">
              No orders registered yet. Click &quot;Create Order&quot; to begin.
            </div>
          ) : (
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
                {recentOrders.map((order) => (
                  <TableRow
                    key={order.id}
                    className="group cursor-pointer hover:bg-[var(--surface-hover)]"
                    onClick={() => navigate(`/orders/${order.id}`)}
                    tabIndex={0}
                    aria-label={`Open order ${order.id}`}
                    onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); navigate(`/orders/${order.id}`); } }}
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
          )}
        </div>
      </section>

      {/* System Trust & Release Visibility Section */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              Underlying Software Release
            </h2>
            <span className="rounded bg-[var(--surface-subtle)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-muted)] border border-[var(--border)]">
              UI Fixture
            </span>
          </div>
          <Link
            to="/release"
            className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] transition-colors"
          >
            <span>Open Release Console</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        <div className="rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <GitCommit size={15} className="text-[var(--text-muted)]" />
                <span className="text-xs text-[var(--text-muted)]">Source Commit:</span>
                <span className="font-mono text-xs font-semibold text-[var(--text-primary)] select-all">
                  {release ? release.source_commit : "N/A"}
                </span>
              </div>
              <p className="text-xs text-[var(--text-secondary)]">
                These release values are demo fixtures and do not identify the running software build.
              </p>
            </div>

            <div className="shrink-0 flex items-center gap-3">
              <div className="text-right">
                <span className="text-[11px] text-[var(--text-muted)] block">Pipeline Controls</span>
                <span className="text-xs font-semibold text-[var(--text-primary)] block">
                  {passedControlsCount} / {totalControlsCount} Reported PASS (demo)
                </span>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => navigate("/release")}
              >
                Inspect
              </Button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
