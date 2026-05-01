/**
 * lib/auth.ts
 * JWT token management — store, retrieve, and clear tokens.
 * Works with localStorage (client-side only).
 */

const ACCESS_KEY = "n7chat_access_token";
const REFRESH_KEY = "n7chat_refresh_token";

export const tokenStore = {
  setTokens(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },

  getAccess(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  },

  getRefresh(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },

  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

/**
 * Decode a JWT payload without verifying signature.
 * Use only for reading non-sensitive claims (role, exp).
 */
export function decodePayload(token: string): Record<string, unknown> {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const json = atob(base64);
    return JSON.parse(json);
  } catch {
    return {};
  }
}

export function getUserRole(token: string): "student" | "admin" | null {
  const payload = decodePayload(token);
  const role = payload["role"];
  if (role === "student" || role === "admin") return role;
  return null;
}

export function isTokenExpired(token: string): boolean {
  const payload = decodePayload(token);
  const exp = payload["exp"] as number | undefined;
  if (!exp) return true;
  return Date.now() / 1000 > exp;
}
