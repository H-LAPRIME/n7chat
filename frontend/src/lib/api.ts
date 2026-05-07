/**
 * lib/api.ts
 * Typed HTTP client for the n7chat Flask backend.
 */

export const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5000";
export const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
export const SUPABASE_LOGOS_BUCKET = process.env.NEXT_PUBLIC_SUPABASE_LOGOS_BUCKET ?? "logos";
export const SUPABASE_PROFILES_BUCKET = process.env.NEXT_PUBLIC_SUPABASE_PROFILES_BUCKET ?? "profiles";

export function supabasePublicUrl(bucket: string, path: string) {
  if (!SUPABASE_URL) return "";
  return `${SUPABASE_URL.replace(/\/$/, "")}/storage/v1/object/public/${bucket}/${path.replace(/^\//, "")}`;
}

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

    me: (token: string) =>
      request<{
        id: string;
        email: string;
        role: string;
        name: string;
        bio: string;
        avatar: string;
      }>("/auth/me", { token }),

    uploadAvatar: async (file: File, token: string) => {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${BASE_URL}/auth/me/avatar`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error ?? "Avatar upload failed");
      }
      return res.json() as Promise<{ message: string; avatar: string }>;
    },

    forgotPassword: (email: string) =>
      request<{ message: string }>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      }),

    resetPassword: (data: { email: string; code: string; new_password: string }) =>
      request<{ message: string }>("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify(data),
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
        `/chat/history?session_id=${encodeURIComponent(sessionId)}`,
        { token }
      ),
  },

  // ── Courses ─────────────────────────────────────────────────
  courses: {
    list: (token: string) =>
      request<{ courses: unknown[] }>("/courses/", { token }),

    create: (data: { title: string; description: string }, token: string) =>
      request<{ message: string; course: unknown }>("/courses/", {
        method: "POST",
        token,
        body: JSON.stringify(data),
      }),

    update: (id: string, data: object, token: string) =>
      request<{ message: string; course: unknown }>(`/courses/${id}`, {
        method: "PUT",
        token,
        body: JSON.stringify(data),
      }),

    delete: (id: string, token: string) =>
      request<{ message: string }>(`/courses/${id}`, {
        method: "DELETE",
        token,
      }),

    recommendations: (token: string) =>
      request<{ recommendations: any[] }>("/courses/recommended", { token }),
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
  // ── Documents ──────────────────────────────────────────────
  documents: {
    list: (token: string) =>
      request<{ documents: unknown[] }>("/documents/", { token }),

    upload: async (file: File, token: string, docType = "autre") => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("doc_type", docType);

      const res = await fetch(`${BASE_URL}/documents/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error ?? "Upload failed");
      }
      return res.json();
    },

    delete: (id: string, token: string) =>
      request<{ message: string }>(`/documents/${id}`, {
        method: "DELETE",
        token,
      }),

    fileUrl: (id: string) => `${BASE_URL}/documents/${id}/file`,

    openFile: async (id: string, token: string) => {
      const res = await fetch(`${BASE_URL}/documents/${id}/file`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error ?? "Unable to open document");
      }

      return URL.createObjectURL(await res.blob());
    },
  },

  // ── Notifications ──────────────────────────────────────────
  notifications: {
    list: (token: string) =>
      request<{ notifications: any[] }>("/notifications/", { token }),

    markAsRead: (id: string, token: string) =>
      request<{ message: string }>(`/notifications/read/${id}`, {
        method: "POST",
        token,
      }),

    broadcast: (data: { title: string; message: string; type?: string }, token: string) =>
      request<{ message: string; notification: any }>("/notifications/broadcast", {
        method: "POST",
        token,
        body: JSON.stringify(data),
      }),
  },
};
