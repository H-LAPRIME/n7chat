/**
 * lib/api.ts
 * Typed HTTP client for the n7chat Flask backend.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5000";

type RequestOptions = RequestInit & { token?: string };

async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { token, headers = {}, ...rest } = options;

  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers as Record<string, string>),
    },
    ...rest,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<{ access_token: string; refresh_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),

    register: (email: string, password: string, role: "student" | "admin") =>
      request<{ message: string }>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, role }),
      }),

    refresh: (refreshToken: string) =>
      request<{ access_token: string }>("/auth/refresh", {
        method: "POST",
        token: refreshToken,
      }),

    logout: (token: string) =>
      request<{ message: string }>("/auth/logout", {
        method: "POST",
        token,
      }),
  },

  // ── Chat ────────────────────────────────────────────────────
  chat: {
    send: (message: string, sessionId: string, token: string) =>
      request<{
        response: string;
        agent_used: string;
        sources: { doc: string; page: number }[];
        session_id: string;
      }>("/chat/", {
        method: "POST",
        token,
        body: JSON.stringify({ message, session_id: sessionId }),
      }),

    history: (sessionId: string, token: string) =>
      request<{ session_id: string; messages: unknown[] }>(
        `/chat/history?session_id=${sessionId}`,
        { token }
      ),
  },

  // ── Courses ─────────────────────────────────────────────────
  courses: {
    list: (token: string) =>
      request<{ courses: unknown[] }>("/courses/", { token }),

    create: (data: { title: string; description: string }, token: string) =>
      request<{ message: string }>("/courses/", {
        method: "POST",
        token,
        body: JSON.stringify(data),
      }),

    update: (id: string, data: object, token: string) =>
      request<{ message: string }>(`/courses/${id}`, {
        method: "PUT",
        token,
        body: JSON.stringify(data),
      }),

    delete: (id: string, token: string) =>
      request<{ message: string }>(`/courses/${id}`, {
        method: "DELETE",
        token,
      }),
  },

  // ── Analytics ───────────────────────────────────────────────
  analytics: {
    get: (token: string) =>
      request<{
        top_questions: string[];
        user_activity: { today: number; week: number };
        errors: { count: number; last: string | null };
      }>("/analytics/", { token }),
  },
};
