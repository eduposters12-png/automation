export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type ApiOptions = RequestInit & {
  json?: unknown;
  responseType?: "json" | "blob";
};

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { json, headers, responseType = "json", ...init } = options;
  const response = await fetch(`${API_URL}${path}`, {
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
    const detail = typeof errorData?.detail === "string" ? errorData.detail : "Something went wrong";
    throw new ApiError(detail, response.status);
  }

  const data = responseType === "blob"
    ? await response.blob()
    : contentType?.includes("application/json")
      ? await response.json()
      : null;

  return data as T;
}
