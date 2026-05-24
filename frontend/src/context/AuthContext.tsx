"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { User, TokenResponse } from "@/lib/types";
import { fetchApi } from "@/lib/api";
import { saveTokens, clearTokens, getAccessToken, decodeJwt } from "@/lib/auth";
import { useRouter } from "next/navigation";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    async function loadUser() {
      const token = getAccessToken();
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const decoded = decodeJwt(token);
        // We can optionally use decoded while fetching to show UI immediately
        if (decoded?.email && decoded.role) {
          setUser({
            id: decoded.sub || decoded.id || "",
            sub: decoded.sub,
            email: decoded.email,
            role: decoded.role,
            is_active: decoded.is_active ?? true,
          });
        }

        const me = await fetchApi<User>("/auth/me");
        setUser(me);
      } catch {
        clearTokens();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }
    loadUser();
  }, []);

  const login = async (email: string, password: string) => {
    const data = await fetchApi<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    saveTokens(data.access_token, data.refresh_token);
    
    // Fetch full profile
    const me = await fetchApi<User>("/auth/me");
    setUser(me);
  };

  const logout = async () => {
    try {
      const refresh = localStorage.getItem("n7_refresh_token");
      if (refresh) {
        await fetchApi("/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refresh_token: refresh }),
        });
      }
    } catch {
      // Ignore
    } finally {
      clearTokens();
      setUser(null);
      router.push("/login"); // Fixed redirection out of dashboard
    }
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
