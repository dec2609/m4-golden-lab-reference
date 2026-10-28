import type { CreateOrderInput, Order } from "../types/order";
import { getApiBaseUrl } from "../config/api";
import { ApiError } from "./apiError";
import { createMockOrdersStore } from "../mocks/orders";
import { validOrderQuantity } from "../config/orders";

export type OrdersScenario = "live" | "populated" | "empty" | "error";
export interface OrdersSource {
  scenario: OrdersScenario;
  revision: number;
  connection: "unverified" | "responding" | "unavailable" | "error";
  detail: string;
  observedAt?: string;
}
interface RequestOptions { signal?: AbortSignal }
export interface OrdersService {
  getOrders(options?: RequestOptions): Promise<Order[]>;
  getOrderById(id: number, options?: RequestOptions): Promise<Order | null>;
  createOrder(input: CreateOrderInput, options?: RequestOptions): Promise<Order>;
  checkHealth(options?: RequestOptions): Promise<{ status: string; isLive: boolean; error?: string }>;
  setScenario(scenario: OrdersScenario): void;
  getScenario(): OrdersScenario;
  isLiveMode(): boolean;
  resetData(): void;
  subscribe(listener: () => void): () => void;
  getSnapshot(): OrdersSource;
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
const nonEmpty = (value: unknown): value is string => typeof value === "string" && !!value.trim();
const positiveInteger = (value: unknown): value is number =>
  typeof value === "number" && Number.isSafeInteger(value) && value > 0;
const statuses = new Set(["pending", "confirmed", "shipped", "cancelled"]);

export function parseOrder(value: unknown): Order {
  if (!record(value) || !positiveInteger(value.id) || !nonEmpty(value.customer_name) ||
      !nonEmpty(value.product_name) || !validOrderQuantity(value.quantity) ||
      typeof value.status !== "string" || !statuses.has(value.status) ||
      typeof value.created_at !== "string" ||
      !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(value.created_at) ||
      !Number.isFinite(Date.parse(value.created_at)) ||
      new Date(value.created_at as string).toISOString().slice(0, 19) !== value.created_at.slice(0, 19)) {
    throw new ApiError("Invalid order response: required fields, types or values do not match the API contract.", { kind: "contract" });
  }
  return { id: value.id, customer_name: value.customer_name, product_name: value.product_name,
    quantity: value.quantity, status: value.status, created_at: value.created_at };
}

export function parseOrders(value: unknown): Order[] {
  if (!record(value) || !Array.isArray(value.orders)) {
    throw new ApiError("Invalid response: expected { orders: [...] }.", { kind: "contract" });
  }
  const orders = value.orders.map(parseOrder);
  if (new Set(orders.map((order) => order.id)).size !== orders.length) {
    throw new ApiError("Invalid response: duplicate order IDs.", { kind: "contract" });
  }
  return orders;
}

export function createOrdersService(config: {
  fetch?: typeof fetch;
  baseUrl?: () => string;
  timeoutMs?: number;
  mockDelayMs?: number;
  initialScenario?: OrdersScenario;
} = {}): OrdersService {
  const initial = config.initialScenario ?? "live";
  const store = createMockOrdersStore();
  if (initial === "empty") store.clearMockOrders();
  let source: OrdersSource = { scenario: initial, revision: 0, connection: "unverified", detail: "No API response observed." };
  let generation = 0;
  let observation = 0;
  const pending = new Set<AbortController>();
  const listeners = new Set<() => void>();
  function publish(next: OrdersSource) { source = next; listeners.forEach((listener) => listener()); }
  const cancelled = () => new ApiError("Request cancelled because its view or data source changed.", { kind: "cancelled" });

  async function request<T>(operation: (signal: AbortSignal, scenario: OrdersScenario) => Promise<T>, options: RequestOptions = {}): Promise<T> {
    const revision = generation;
    const scenario = source.scenario;
    const attempt = ++observation;
    const controller = new AbortController();
    pending.add(controller);
    const abort = () => controller.abort(cancelled());
    options.signal?.addEventListener("abort", abort, { once: true });
    if (options.signal?.aborted) abort();
    let timeout: ReturnType<typeof setTimeout> | undefined;
    let onAbort: () => void = () => {};
    const interrupted = new Promise<never>((_, reject) => {
      onAbort = () => reject(controller.signal.reason ?? cancelled());
      controller.signal.addEventListener("abort", onAbort, { once: true });
      if (controller.signal.aborted) onAbort();
      timeout = setTimeout(() => controller.abort(new ApiError("API request timed out.", { kind: "timeout", isNetworkError: true })), config.timeoutMs ?? 10000);
    });
    const observe = (connection: OrdersSource["connection"], detail: string) => {
      if (scenario === "live" && revision === generation && attempt === observation) {
        publish({ scenario, revision, connection, detail, observedAt: new Date().toISOString() });
      }
    };
    try {
      const value = await Promise.race([
        Promise.resolve().then(() => {
          if (controller.signal.aborted) throw controller.signal.reason;
          return operation(controller.signal, scenario);
        }), interrupted,
      ]);
      if (revision !== generation || controller.signal.aborted) throw cancelled();
      observe("responding", "Last API response passed frontend validation.");
      return value;
    } catch (error) {
      const failure = error instanceof ApiError ? error : new ApiError("Unable to reach the API.", { kind: "network", isNetworkError: true });
      if (failure.kind !== "cancelled") observe(failure.isNetworkError ? "unavailable" : "error", failure.message);
      throw failure;
    } finally {
      clearTimeout(timeout);
      controller.signal.removeEventListener("abort", onAbort);
      options.signal?.removeEventListener("abort", abort);
      pending.delete(controller);
    }
  }

  async function json(path: string, init: RequestInit, signal: AbortSignal, expectedStatus: number): Promise<unknown> {
    const response = await (config.fetch ?? globalThis.fetch)(`${(config.baseUrl ?? getApiBaseUrl)()}${path}`, { ...init, signal });
    if (!response.ok) {
      let message = `API returned HTTP ${response.status}.`;
      try { const body: unknown = await response.json(); if (record(body) && nonEmpty(body.error)) message = body.error; } catch { /* Keep the HTTP error. */ }
      throw new ApiError(message, { status: response.status, kind: "http" });
    }
    if (response.status !== expectedStatus) throw new ApiError(`Unexpected HTTP success status ${response.status}; expected ${expectedStatus}.`, { status: response.status, kind: "contract" });
    if (!/^application\/json(?:\s*;|$)/i.test(response.headers.get("Content-Type") ?? "")) {
      throw new ApiError("API success response is not application/json.", { status: response.status, kind: "contract" });
    }
    try { return await response.json(); } catch {
      throw new ApiError("API returned malformed JSON.", { status: response.status, kind: "contract" });
    }
  }
  async function mockPause(signal: AbortSignal, scenario: OrdersScenario) {
    await new Promise((resolve) => setTimeout(resolve, config.mockDelayMs ?? 300));
    if (signal.aborted) throw signal.reason;
    if (scenario === "error") throw new ApiError("Simulated order service error (HTTP 500).", { status: 500 });
  }

  const service: OrdersService = {
    subscribe(listener) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    getSnapshot: () => source,
    isLiveMode: () => source.scenario === "live",
    getScenario: () => source.scenario,
    setScenario(scenario) {
      generation++;
      pending.forEach((controller) => controller.abort(cancelled()));
      if (scenario === "empty") store.clearMockOrders();
      if (scenario === "populated") store.resetMockOrders();
      publish({ scenario, revision: generation, connection: "unverified", detail: "No API response observed for this selection." });
    },
    resetData() { store.resetMockOrders(); service.setScenario(initial); },
    getOrders(options) {
      return request(async (signal, scenario) => {
        if (scenario === "live") return parseOrders(await json("/orders", { headers: { Accept: "application/json" } }, signal, 200));
        await mockPause(signal, scenario);
        return store.getMockOrders();
      }, options);
    },
    async getOrderById(id, options) {
      if (!positiveInteger(id)) throw new ApiError("Invalid order ID.", { status: 400 });
      return (await service.getOrders(options)).find((order) => order.id === id) ?? null;
    },
    async createOrder(input, options) {
      if (!record(input) || !nonEmpty(input.customer_name) || !nonEmpty(input.product_name) || !validOrderQuantity(input.quantity)) {
        throw new ApiError("Customer and product must be non-empty strings; quantity must be an integer between 1 and 2147483647.", { status: 400 });
      }
      const payload = { customer_name: input.customer_name.trim(), product_name: input.product_name.trim(), quantity: input.quantity };
      const live = service.isLiveMode();
      try {
        return await request(async (signal, scenario) => {
          if (scenario === "live") {
            const order = parseOrder(await json("/orders", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(payload) }, signal, 201));
            if (order.customer_name !== payload.customer_name || order.product_name !== payload.product_name || order.quantity !== payload.quantity || order.status !== "pending") {
              throw new ApiError("Created order does not match the submitted payload.", { kind: "contract" });
            }
            return order;
          }
          await mockPause(signal, scenario);
          return store.addMockOrder(payload);
        }, options);
      } catch (error) {
        if (live && error instanceof ApiError) {
          throw new ApiError(`${error.message} Creation was not confirmed. Refresh orders before retrying; the server may have received the request.`, {
            status: error.status, kind: error.kind, isNetworkError: error.isNetworkError,
          });
        }
        throw error;
      }
    },
    async checkHealth(options) {
      try {
        return await request(async (signal, scenario) => {
          if (scenario !== "live") return { status: "mock", isLive: false };
          const body = await json("/health", { headers: { Accept: "application/json" } }, signal, 200);
          if (!record(body) || body.status !== "ok") throw new ApiError("Invalid liveness response.", { kind: "contract" });
          return { status: "ok", isLive: true };
        }, options);
      } catch (error) {
        if (error instanceof ApiError && error.kind === "cancelled") throw error;
        return { status: "unavailable", isLive: false, error: error instanceof Error ? error.message : "Health check failed." };
      }
    },
  };
  return service;
}

export const ordersService = createOrdersService({
  initialScenario: import.meta.env.VITE_USE_MOCK === "true" ? "populated" : "live",
});
