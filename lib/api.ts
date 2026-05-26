export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

function getApiUrl() {
  if (typeof window === "undefined") {
    return API_URL;
  }

  try {
    const url = new URL(API_URL);
    const browserHost = window.location.hostname;
    const localHosts = new Set(["localhost", "127.0.0.1"]);
    if (localHosts.has(url.hostname) && localHosts.has(browserHost)) {
      url.hostname = browserHost;
      return url.toString().replace(/\/$/, "");
    }
  } catch {
    return API_URL;
  }

  return API_URL;
}

export class ApiError extends Error {
  status: number;
  detail?: any;
  code?: string;

  constructor(message: string, status: number, detail?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.code = typeof detail?.code === "string" ? detail.code : undefined;
  }
}

type ApiOptions = RequestInit & {
  json?: unknown;
  responseType?: "json" | "blob";
};

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { json, headers, responseType = "json", ...init } = options;
  const response = await fetch(`${getApiUrl()}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(json ? { "Content-Type": "application/json" } : {}),
      ...headers
    },
    body: json ? JSON.stringify(json) : init.body
  });

  const contentType = response.headers.get("content-type");
  const errorData = !response.ok && contentType?.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    const detail = errorData?.detail;
    if (detail && typeof detail === "object" && !Array.isArray(detail)) {
      throw new ApiError(typeof detail.message === "string" ? detail.message : "Something went wrong", response.status, detail);
    }
    throw new ApiError(typeof detail === "string" ? detail : "Something went wrong", response.status);
  }

  const data = responseType === "blob"
    ? await response.blob()
    : contentType?.includes("application/json")
      ? await response.json()
      : null;

  return data as T;
}
