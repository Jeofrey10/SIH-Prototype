/** API HTTP Client with token injection and error handling. */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, string>;
  request_id?: string;
  status: number;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = sessionStorage.getItem("aicte_token") || localStorage.getItem("aicte_token");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = endpoint.startsWith("http") ? endpoint : `${BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized
  if (response.status === 401 && !endpoint.includes("/auth/login")) {
    sessionStorage.removeItem("aicte_token");
    sessionStorage.removeItem("aicte_user");
    window.dispatchEvent(new Event("aicte_auth_unauthorized"));
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  // Check content type for CSV or JSON
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("text/csv")) {
    const text = await response.text();
    return text as unknown as T;
  }

  let data: any;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const errorPayload = data?.error || {};
    const apiError: ApiError = {
      code: errorPayload.code || "REQUEST_FAILED",
      message: errorPayload.message || data?.detail || `Request failed with status ${response.status}`,
      details: errorPayload.details || {},
      request_id: errorPayload.request_id || response.headers.get("X-Request-ID") || "",
      status: response.status,
    };
    throw apiError;
  }

  return data as T;
}

export async function downloadCsv(endpoint: string, fallbackFilename: string): Promise<void> {
  const token = sessionStorage.getItem("aicte_token") || localStorage.getItem("aicte_token");
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = endpoint.startsWith("http") ? endpoint : `${BASE_URL}${endpoint}`;
  const response = await fetch(url, { headers });

  if (!response.ok) {
    throw new Error("Failed to export report CSV");
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition");
  let filename = fallbackFilename;
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
}
