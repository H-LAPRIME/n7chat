/**
 * app/(auth)/login/page.tsx
 * 2-Step Login with "Swipe" effect.
 */
"use client";

import { useState, FormEvent, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { tokenStore } from "@/lib/auth";
import { Mail, Lock, ArrowRight, ArrowLeft, LogIn, CheckCircle2 } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Validation
  const canGoNext = () => {
    if (step === 0) return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    return true;
  };

  const nextStep = () => {
    if (canGoNext()) {
      setError("");
      setStep(1);
    } else {
      setError("Veuillez entrer un email valide.");
    }
  };

  const prevStep = () => {
    setError("");
    setStep(0);
  };

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    
    // Step 0 -> Step 1
    if (step === 0) {
      if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        setError("");
        setStep(1);
      } else {
        setError("Veuillez entrer une adresse email valide.");
      }
      return;
    }

    // Final Step (1) -> Login API Call
    if (step === 1) {
      if (password.length === 0) {
        setError("Veuillez entrer votre mot de passe.");
        return;
      }

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
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden relative">
        
        {/* Progress Bar Animation */}
        <div className="absolute top-0 left-0 w-full h-1 bg-slate-100 z-50">
          <div 
            className="h-full bg-brand transition-all duration-700 ease-[cubic-bezier(0.34,1.56,0.64,1)] shadow-[0_0_10px_rgba(var(--brand-rgb),0.5)]"
            style={{ width: step === 0 ? "50%" : "100%" }}
          />
        </div>

        <div className="p-8">
          {/* Header */}
          <div className="mb-10 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand/5 text-brand mb-4">
              <LogIn size={32} />
            </div>
            <h1 className="text-3xl font-serif font-bold text-slate-900">
              n7<span className="text-brand">chat</span>
            </h1>
            <p className="mt-2 text-sm text-slate-500 font-medium">
              {step === 0 ? "Content de vous revoir !" : "Entrez votre mot de passe"}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="relative overflow-hidden">
            {/* Step Container (Swipe Effect) */}
            <div 
              className="flex transition-transform duration-700 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
              style={{ transform: `translateX(-${step * 100}%)` }}
            >
              {/* Step 0: Email */}
              <div className="w-full shrink-0 px-1">
                <div className="relative group">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-brand transition-colors" size={18} />
                    <input
                      type="email"
                      placeholder="votre.email@ecole.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-10 pr-4 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand/5 transition-all"
                    />
                </div>
              </div>

              {/* Step 1: Password */}
              <div className="w-full shrink-0 px-1">
                <div className="relative group">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-brand transition-colors" size={18} />
                    <input
                      type="password"
                      placeholder="Votre mot de passe"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-10 pr-4 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand/5 transition-all"
                    />
                </div>
                <div className="mt-2 text-right">
                  <a href="/forgot-password" className="text-[10px] font-bold text-brand uppercase tracking-wider hover:underline">Mot de passe oublié ?</a>
                </div>
              </div>
            </div>

            {error && (
              <p className="mt-6 text-center text-xs font-semibold text-red-500 bg-red-50 py-2 rounded-lg animate-shake">
                {error}
              </p>
            )}

            {/* Actions */}
            <div className="mt-6 flex gap-3">
              {step > 0 && (
                <button
                  type="button"
                  onClick={prevStep}
                  className="flex items-center justify-center w-14 h-12 rounded-xl border border-slate-200 text-slate-500 hover:bg-slate-50 transition-all active:scale-95"
                >
                  <ArrowLeft size={20} />
                </button>
              )}
              <button
                type="submit"
                disabled={loading || !canGoNext()}
                className={`flex-1 h-12 flex items-center justify-center gap-2 rounded-xl font-bold text-white transition-all active:scale-[0.98] shadow-lg ${
                  loading || !canGoNext() ? "bg-slate-300 cursor-not-allowed" : "bg-brand hover:bg-brand-hover shadow-brand/20"
                }`}
              >
                {loading ? "Connexion..." : step === 1 ? "Se connecter" : "Suivant"}
                {step === 0 && <ArrowRight size={18} />}
                {step === 1 && !loading && <CheckCircle2 size={18} />}
              </button>
            </div>
          </form>

          <p className="mt-8 text-center text-xs text-slate-400">
            Nouveau ici ?{" "}
            <a href="/register" className="text-brand font-bold hover:underline">Créer un compte</a>
          </p>
        </div>
      </div>
    </main>
  );
}

