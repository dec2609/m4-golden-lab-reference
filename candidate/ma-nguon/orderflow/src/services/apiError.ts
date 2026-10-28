/**
 * Standardized API Error for OrderFlow
 */
export class ApiError extends Error {
  public status?: number;
  public isNetworkError: boolean;
  public details?: unknown;
  public kind: "http" | "network" | "contract" | "timeout" | "cancelled";

  constructor(
    message: string,
    options?: {
      status?: number;
      isNetworkError?: boolean;
      details?: unknown;
      kind?: ApiError["kind"];
    }
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options?.status;
    this.isNetworkError = options?.isNetworkError ?? false;
    this.details = options?.details;
    this.kind = options?.kind ?? (this.isNetworkError ? "network" : "http");
  }
}
