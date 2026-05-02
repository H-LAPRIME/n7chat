/**
 * app/(auth)/forgot-password/page.tsx
 * OTP based password reset flow.
 */
"use client";

import { useState, FormEvent } from "react";
import { Mail, ArrowLeft, Send, CheckCircle2, Lock, Hash } from "lucide-react";
import { useRouter } from "next/navigation";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState(1); // 1: Email, 2: Code & New Password
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  // Step 1: Request Code
  async function handleRequestCode(e: FormEvent) {
    e.preventDefault();
    if (!email) return setError("Veuillez entrer votre email.");

    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Une erreur est survenue.");
      
      setMessage("Un code de 6 chiffres a été envoyé à votre email.");
      setStep(2);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  // Step 2: Reset Password with Code
  async function handleResetPassword(e: FormEvent) {
    e.preventDefault();
    if (password !== confirmPassword) return setError("Les mots de passe ne correspondent pas.");
    if (code.length !== 6) return setError("Le code doit comporter 6 chiffres.");

    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code, new_password: password }),
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Code invalide ou expiré.");
      
      setMessage("Succès ! Votre mot de passe a été mis à jour.");
      setTimeout(() => router.push("/login"), 2000);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden relative">
        {/* Progress Bar Animation */}
        <div className="absolute top-0 left-0 w-full h-1 bg-slate-100 z-50">
          <div 
            className="h-full bg-brand transition-all duration-700 ease-[cubic-bezier(0.34,1.56,0.64,1)] shadow-[0_0_10px_rgba(var(--brand-rgb),0.5)]"
            style={{ width: step === 1 ? "50%" : "100%" }}
          />
        </div>

        <div className="p-8">
          {step === 1 ? (
            <>
              <div className="mb-10 text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand/5 text-brand mb-4">
                  <Mail size={32} />
                </div>
                <h1 className="text-3xl font-serif font-bold text-slate-900">Récupération</h1>
                <p className="mt-2 text-sm text-slate-500 font-medium">
                  Entrez votre email pour recevoir un code de sécurité.
                </p>
              </div>

              <form onSubmit={handleRequestCode}>
                <div className="relative group">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-brand transition-colors" size={18} />
                  <input
                    type="email"
                    placeholder="votre.email@ecole.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-10 pr-4 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand/5 transition-all"
                    required
                  />
                </div>

                {error && <p className="mt-4 text-center text-xs font-semibold text-red-500 bg-red-50 py-2 rounded-lg">{error}</p>}

                <div className="mt-8 flex gap-3">
                  <a href="/login" className="flex items-center justify-center w-14 h-12 rounded-xl border border-slate-200 text-slate-500 hover:bg-slate-50 transition-all active:scale-95">
                    <ArrowLeft size={20} />
                  </a>
                  <button type="submit" disabled={loading} className={`flex-1 h-12 flex items-center justify-center gap-2 rounded-xl font-bold text-white transition-all active:scale-[0.98] ${loading ? "bg-slate-300" : "bg-brand hover:bg-brand-hover shadow-lg shadow-brand/20"}`}>
                    {loading ? "Envoi..." : "Envoyer le code"}
                    {!loading && <Send size={18} />}
                  </button>
                </div>
              </form>
            </>
          ) : (
            <>
              <div className="mb-10 text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand/5 text-brand mb-4">
                  <Hash size={32} />
                </div>
                <h1 className="text-3xl font-serif font-bold text-slate-900">Vérification</h1>
                <p className="mt-2 text-sm text-slate-500 font-medium">
                  Saisissez le code envoyé à <span className="text-slate-900 font-bold">{email}</span>.
                </p>
              </div>

              <form onSubmit={handleResetPassword} className="space-y-4">
                <div className="relative group">
                  <Hash className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-brand transition-colors" size={18} />
                  <input
                    type="text"
                    maxLength={6}
                    placeholder="Code à 6 chiffres"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-10 pr-4 text-sm font-mono tracking-[0.5em] outline-none focus:border-brand focus:ring-4 focus:ring-brand/5 transition-all text-center"
                    required
                  />
                </div>

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

                {error && <p className="mt-4 text-center text-xs font-semibold text-red-500 bg-red-50 py-2 rounded-lg">{error}</p>}
                {message && (
                  <div className="mt-4 flex items-center gap-2 p-3 bg-green-50 text-green-700 rounded-xl text-xs font-medium">
                    <CheckCircle2 size={16} />
                    <p>{message}</p>
                  </div>
                )}

                <button type="submit" disabled={loading} className={`w-full h-12 flex items-center justify-center gap-2 rounded-xl font-bold text-white transition-all active:scale-[0.98] ${loading ? "bg-slate-300" : "bg-brand hover:bg-brand-hover shadow-lg shadow-brand/20"}`}>
                  {loading ? "Vérification..." : "Réinitialiser"}
                </button>
                
                <button type="button" onClick={() => setStep(1)} className="w-full text-center text-xs text-slate-400 hover:text-brand font-medium transition-colors">
                  Renvoyer le code ou changer d'email
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
