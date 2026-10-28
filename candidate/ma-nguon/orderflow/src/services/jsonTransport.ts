import { ApiError } from "./apiError";

export function sameOriginPath(value: string): string {
  if (!/^\/(?!\/)[A-Za-z0-9/_.-]+$/.test(value) || value.includes("..")) {
    throw new ApiError("Expected a same-origin path without credentials, query or fragment.", { kind: "contract" });
  }
  return value;
}

/** Bounded GET transport. A timeout includes headers and body; no retries. */
export async function getJson(path: string, options: {
  signal?: AbortSignal; timeoutMs?: number; fetch?: typeof fetch;
  statuses?: number[]; noBodyStatuses?: number[]; maxBytes?: number;
} = {}): Promise<{ status: number; body: unknown }> {
  const controller = new AbortController();
  const abort = () => controller.abort(new ApiError("Request cancelled.", { kind: "cancelled" }));
  options.signal?.addEventListener("abort", abort, { once: true });
  if (options.signal?.aborted) abort();
  let timer: ReturnType<typeof setTimeout> | undefined;
  let onAbort: () => void = () => {};
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  const interrupted = new Promise<never>((_, reject) => {
    onAbort = () => {
      void reader?.cancel().catch(() => {});
      reject(controller.signal.reason);
    };
    controller.signal.addEventListener("abort", onAbort, { once: true });
    if (controller.signal.aborted) onAbort();
    timer = setTimeout(() => controller.abort(new ApiError("Evidence/API request timed out.", { kind: "timeout" })), options.timeoutMs ?? 10000);
  });
  try {
    const operation = async () => {
      if (controller.signal.aborted) throw controller.signal.reason;
      const res = await (options.fetch ?? globalThis.fetch)(path, {
        signal: controller.signal, method: "GET", headers: { Accept: "application/json" },
        credentials: "same-origin", redirect: "error", cache: "no-store",
      });
      if (!(options.statuses ?? [200]).includes(res.status)) throw new ApiError("Source returned HTTP " + res.status + ".", { kind: "http", status: res.status });
      if ((options.noBodyStatuses ?? []).includes(res.status)) return { status: res.status, body: null };
      if (!/^application\/json(?:\s*;|$)/i.test(res.headers.get("Content-Type") ?? "")) throw new ApiError("Expected application/json response.", { kind: "contract" });
      const limit = options.maxBytes ?? 1024 * 1024;
      if (Number(res.headers.get("Content-Length")) > limit) throw new ApiError("JSON response exceeds size limit.", { kind: "contract" });
      let text = "";
      if (res.body) {
        reader = res.body.getReader();
        const decoder = new TextDecoder();
        let bytes = 0;
        try {
          while (true) {
            if (controller.signal.aborted) throw controller.signal.reason;
            const chunk = await reader.read();
            if (chunk.done) break;
            bytes += chunk.value.byteLength;
            if (bytes > limit) throw new ApiError("JSON response exceeds size limit.", { kind: "contract" });
            text += decoder.decode(chunk.value, { stream: true });
          }
          text += decoder.decode();
        } finally {
          void reader.cancel().catch(() => {});
          reader.releaseLock();
        }
      } else {
        text = await res.text();
        if (new TextEncoder().encode(text).length > limit) throw new ApiError("JSON response exceeds size limit.", { kind: "contract" });
      }
      if (!text.trim()) return { status: res.status, body: null };
      try { return { status: res.status, body: JSON.parse(text) as unknown }; }
      catch { throw new ApiError("Source returned malformed JSON.", { kind: "contract" }); }
    };
    return await Promise.race([operation(), interrupted]);
  } catch (error) {
    if (controller.signal.aborted) throw controller.signal.reason;
    if (error instanceof ApiError) throw error;
    throw new ApiError("Evidence/API source unavailable.", { kind: "network", isNetworkError: true });
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener("abort", abort);
    controller.signal.removeEventListener("abort", onAbort);
  }
}
