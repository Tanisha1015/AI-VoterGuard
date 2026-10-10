/**
 * Thin HTTP client for the core and trust services.
 * When VITE_USE_MOCKS === "true", requests are answered from src/mocks (see mockRouter.ts).
 */
import type { ApiErrorBody } from "./types";
import { MockHttpError, resolveMock, type MockVerifyBody } from "./mockRouter";
import { readFileText } from "../lib/readFile";

export type Service = "core" | "trust";

/** HTTP error carrying the contract's {"error": {code, message}} body when available. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

/** The service could not be reached (offline, DNS, CORS, server down). */
export class NetworkError extends Error {
  constructor(message = "Network request failed") {
    super(message);
    this.name = "NetworkError";
  }
}

const DEFAULT_MOCK_DELAY_MS = 300;

/** True when the app should use local synthetic fixtures. */
export function useMocks(): boolean {
  return import.meta.env.VITE_USE_MOCKS === "true";
}

/** Base URL for a service, without trailing slash. */
export function baseUrl(service: Service): string {
  const raw =
    service === "core"
      ? (import.meta.env.VITE_CORE_URL ?? "http://localhost:8000")
      : (import.meta.env.VITE_TRUST_URL ?? "http://localhost:8002");
  return raw.replace(/\/+$/, "");
}

function mockDelay(): number {
  const raw = import.meta.env.VITE_MOCK_DELAY_MS;
  const parsed = raw === undefined ? NaN : Number(raw);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : DEFAULT_MOCK_DELAY_MS;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

type Method = "GET" | "POST" | "PUT";

/** Mock mode cannot hash files, so multipart bodies are passed to the mock layer as text. */
async function toMockBody(body: unknown): Promise<unknown> {
  if (typeof FormData === "undefined" || !(body instanceof FormData)) return body;
  const file = body.get("file");
  const reportId = body.get("report_id");
  const fileText: MockVerifyBody["fileText"] = file instanceof Blob ? await readFileText(file) : "";
  return { fileText, reportId: typeof reportId === "string" && reportId ? reportId : null } satisfies MockVerifyBody;
}

async function mockRequest<T>(service: Service, method: Method, path: string, body?: unknown): Promise<T> {
  await sleep(mockDelay());
  const mockBody = await toMockBody(body);
  try {
    return resolveMock<T>(service, method, path, mockBody);
  } catch (error) {
    if (error instanceof MockHttpError) throw new ApiError(error.status, error.code, error.message);
    throw error;
  }
}

async function request<T>(service: Service, method: Method, path: string, body?: unknown): Promise<T> {
  if (useMocks()) return mockRequest<T>(service, method, path, body);

  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${baseUrl(service)}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
    });
  } catch {
    throw new NetworkError();
  }

  if (!response.ok) {
    throw await toApiError(response);
  }
  return (await response.json()) as T;
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const data = (await response.json()) as Partial<ApiErrorBody>;
    if (data.error && typeof data.error.code === "string") {
      return new ApiError(response.status, data.error.code, data.error.message ?? response.statusText);
    }
  } catch {
    // body was not JSON; fall through
  }
  return new ApiError(response.status, `HTTP_${response.status}`, response.statusText || "Request failed");
}

export function apiGet<T>(service: Service, path: string): Promise<T> {
  return request<T>(service, "GET", path);
}

export function apiPost<T>(service: Service, path: string, body?: unknown): Promise<T> {
  return request<T>(service, "POST", path, body);
}

export function apiPut<T>(service: Service, path: string, body?: unknown): Promise<T> {
  return request<T>(service, "PUT", path, body);
}

/**
 * GET a file as a raw Blob, without JSON parsing or re-encoding, so its bytes (and hash)
 * stay exactly as stored. In mock mode the mock route returns the file text.
 */
export async function apiGetBlob(service: Service, path: string, type = "application/json"): Promise<Blob> {
  if (useMocks()) {
    const text = await mockRequest<string>(service, "GET", path);
    return new Blob([text], { type });
  }
  let response: Response;
  try {
    response = await fetch(`${baseUrl(service)}${path}`);
  } catch {
    throw new NetworkError();
  }
  if (!response.ok) throw await toApiError(response);
  return response.blob();
}
