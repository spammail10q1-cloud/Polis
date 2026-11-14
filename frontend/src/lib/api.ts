import type { ApiError } from "./types";

const BASE = "/api/v1";

export class ApiRequestError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    const message =
      typeof detail === "string"
        ? detail
        : typeof detail === "object" && detail && "message" in detail
          ? String((detail as { message?: string }).message)
          : `Request failed (${status})`;
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.detail = detail;
  }
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (typeof error.detail === "string") return error.detail;
    if (error.detail && typeof error.detail === "object") {
      const detail = error.detail as { errors?: string[]; message?: string };
      if (detail.message) return detail.errors?.length ? `${detail.message} ${detail.errors[0]}` : detail.message;
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  const contentType = response.headers.get("content-type") || "";
  let body: unknown = null;
  if (response.status !== 204) {
    if (contentType.includes("application/json")) {
      body = await response.json().catch(() => null);
    } else {
      body = await response.text().catch(() => null);
    }
  }
  if (!response.ok) {
    const detail = (body as ApiError | null)?.detail ?? body ?? response.statusText;
    if (response.status === 401 && typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("polis:unauthorized"));
    }
    throw new ApiRequestError(response.status, detail);
  }
  return body as T;
}

export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, { method: "POST", body: JSON.stringify(body) });
}

export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, { method: "PATCH", body: JSON.stringify(body) });
}

export function apiDelete<T = { ok: boolean }>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "DELETE" });
}

export async function uploadFile<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<T>(path, { method: "POST", body: form });
}

export async function downloadExport(): Promise<Blob> {
  const response = await fetch(`${BASE}/privacy/export`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiRequestError(response.status, (body as ApiError | null)?.detail ?? "Export failed");
  }
  return response.blob();
}
