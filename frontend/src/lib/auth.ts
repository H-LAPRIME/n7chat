export function saveTokens(access_token: string, refresh_token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("n7_access_token", access_token);
    localStorage.setItem("n7_refresh_token", refresh_token);
  }
}

export function getAccessToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("n7_access_token");
  }
  return null;
}

export function getRefreshToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("n7_refresh_token");
  }
  return null;
}

export function clearTokens() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("n7_access_token");
    localStorage.removeItem("n7_refresh_token");
  }
}

export type JwtPayload = {
  sub?: string;
  id?: string;
  email?: string;
  role?: "student" | "teacher" | "admin";
  is_active?: boolean;
  exp?: number;
  iat?: number;
};

export function decodeJwt(token: string): JwtPayload | null {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}
