/**
 * app/(auth)/reset-password/page.tsx
 * Set a new password using a token.
 */
"use client";

import { useState, FormEvent, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Lock, ArrowRight, CheckCircle2 } from "lucide-react";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (password !== confirmPassword) return setError("Les mots de passe ne correspondent pas.");
    if (password.length < 8) return setError("Le mot de passe doit faire au moins 8 caractères.");

    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Une erreur est survenue.");
      
      setSuccess(true);
      setTimeout(() => router.push("/login"), 3000);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="text-center p-8">
        <p className="text-red-500 font-bold">Jeton manquant ou invalide.</p>
        <a href="/login" className="mt-4 inline-block text-brand font-bold underline">Retour à la connexion</a>
      </div>
    );
  }

  if (success) {
    return (
      <div className="text-center p-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-50 text-green-500 mb-6">
          <CheckCircle2 size={40} />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">Mot de passe réinitialisé !</h2>
        <p className="text-slate-500">Vous allez être redirigé vers la page de connexion...</p>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-10 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand/5 text-brand mb-4">
          <Lock size={32} />
        </div>
        <h1 className="text-3xl font-serif font-bold text-slate-900">Nouveau mot de passe</h1>
        <p className="mt-2 text-sm text-slate-500 font-medium">Choisissez un mot de passe fort et sécurisé.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative group">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-brand transition-colors" size={18} />
          <input
            type="password"
            placeholder="Nouveau mot de passe"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-10 pr-4 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand/5 transition-all"
            required
          />
        </div>

        <div className="relative group">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-brand transition-colors" size={18} />
          <input
            type="password"
            placeholder="Confirmer le mot de passe"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-10 pr-4 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand/5 transition-all"
            required
          />
        </div>

        {error && (
          <p className="mt-4 text-center text-xs font-semibold text-red-500 bg-red-50 py-2 rounded-lg">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className={`w-full mt-6 h-12 flex items-center justify-center gap-2 rounded-xl font-bold text-white transition-all active:scale-[0.98] shadow-lg ${
            loading ? "bg-slate-300" : "bg-brand hover:bg-brand-hover shadow-brand/20"
          }`}
        >
          {loading ? "Mise à jour..." : "Réinitialiser"}
          {!loading && <ArrowRight size={18} />}
        </button>
      </form>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden relative">
        <div className="absolute top-0 left-0 w-full h-1 bg-brand shadow-[0_0_10px_rgba(185,28,28,0.5)]" />
        <Suspense fallback={<div className="p-8 text-center">Chargement...</div>}>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </main>
  );
}
