import { getAccessToken, getRefreshToken, saveTokens, clearTokens } from "./auth";

const API_BASE = "http://localhost:8000";

let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

export async function fetchApi<T = unknown>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const token = getAccessToken();

  const headers = new Headers(options.headers || {});
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  /* Remove content type if body is FormData because browser needs to set the boundary */
  if (options.body instanceof FormData) {
    headers.delete("Content-Type");
  }

  let response = await fetch(url, { ...options, headers });

  if (response.status === 401 && endpoint !== "/auth/login") {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearTokens();
      throw new Error("Unauthorized");
    }

    if (!isRefreshing) {
      isRefreshing = true;
      try {
        const refreshResponse = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!refreshResponse.ok) {
          clearTokens();
          throw new Error("Refresh failed");
        }

        const data = await refreshResponse.json();
        saveTokens(data.access_token, data.refresh_token);
        isRefreshing = false;
        onRefreshed(data.access_token);
        
        // Retry the original request
        headers.set("Authorization", `Bearer ${data.access_token}`);
        response = await fetch(url, { ...options, headers });
      } catch {
        isRefreshing = false;
        clearTokens();
        throw new Error("Unauthorized");
      }
    } else {
      // Wait for the token refresh to complete then retry
      return new Promise((resolve, reject) => {
        subscribeTokenRefresh(async (newToken) => {
          headers.set("Authorization", `Bearer ${newToken}`);
          try {
            const res = await fetch(url, { ...options, headers });
            resolve(handleResponse<T>(res));
          } catch (error) {
            reject(error);
          }
        });
      });
    }
  }

  return handleResponse<T>(response);
}

async function handleResponse<T = unknown>(response: Response): Promise<T> {
  if (response.status === 204) {
    return null as T;
  }
  
  const text = await response.text();
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    data = text;
  }

  if (!response.ok) {
    const detail =
      typeof data === "object" && data !== null && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : response.statusText;
    const error = new Error(detail) as Error & { status?: number; data?: unknown };
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data as T;
}

export function getApiUrl() {
  return API_BASE;
}
