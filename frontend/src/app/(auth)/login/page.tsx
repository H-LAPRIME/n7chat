/**
 * app/(auth)/login/page.tsx
 * Login page — FR/AR/EN multi-language ready.
 */
"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { tokenStore } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { access_token, refresh_token } = await api.auth.login(email, password);
      tokenStore.setTokens(access_token, refresh_token);
      router.push("/chat");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-[#0f0f1a] px-4">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md p-8 shadow-2xl">
        {/* Logo */}
        <div className="mb-6 text-center">
          <span className="text-3xl font-bold tracking-tight text-white">
            n7<span className="text-[#6C5CE7]">chat</span>
          </span>
          <p className="mt-1 text-sm text-white/50">Plateforme éducative IA</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block mb-1 text-xs font-medium text-white/70 uppercase tracking-wider">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-white placeholder-white/30 outline-none focus:border-[#6C5CE7] focus:ring-1 focus:ring-[#6C5CE7] transition"
              placeholder="vous@example.com"
            />
          </div>

          <div>
            <label className="block mb-1 text-xs font-medium text-white/70 uppercase tracking-wider">
              Mot de passe
            </label>
            <input
              id="login-password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-white placeholder-white/30 outline-none focus:border-[#6C5CE7] focus:ring-1 focus:ring-[#6C5CE7] transition"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-2 text-sm text-red-400">
              {error}
            </p>
          )}

          <button
            id="login-submit"
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-[#6C5CE7] py-2.5 font-semibold text-white hover:bg-[#5a4bd1] disabled:opacity-50 transition-colors"
          >
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-white/40">
          Pas encore de compte ?{" "}
          <a href="/register" className="text-[#6C5CE7] hover:underline">
            S&apos;inscrire
          </a>
        </p>
      </div>
    </main>
  );
}
