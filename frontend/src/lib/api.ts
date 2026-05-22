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

export async function fetchApi(endpoint: string, options: RequestInit = {}): Promise<any> {
  const url = `${API_BASE}${endpoint}`;
  let token = getAccessToken();

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
      } catch (err) {
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
            resolve(handleResponse(res));
          } catch (err) {
            reject(err);
          }
        });
      });
    }
  }

  return handleResponse(response);
}

async function handleResponse(response: Response) {
  if (response.status === 204) {
    return null;
  }
  
  const text = await response.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch (e) {
    data = text;
  }

  if (!response.ok) {
    const error = new Error(data?.detail || response.statusText);
    (error as any).status = response.status;
    (error as any).data = data;
    throw error;
  }

  return data;
}

export function getApiUrl() {
  return API_BASE;
}
