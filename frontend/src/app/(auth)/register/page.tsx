/**
 * app/(auth)/register/page.tsx
 * 3-Step Student Registration with "Swipe" effect.
 */
"use client";

import { useState, FormEvent, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { tokenStore } from "@/lib/auth";
import { User, Mail, Lock, ArrowRight, ArrowLeft, GraduationCap, CheckCircle2 } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Validation for each step
  const canGoNext = () => {
    if (step === 0) return formData.firstName.trim() && formData.lastName.trim();
    if (step === 1) return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email);
    if (step === 2) return formData.password.length >= 8 && formData.password === formData.confirmPassword;
    return false;
  };

  const nextStep = () => {
    if (canGoNext()) {
      setError("");
      setStep((s) => s + 1);
    } else {
      setError("Veuillez remplir correctement les champs.");
    }
  };

  const prevStep = () => {
    setError("");
    setStep((s) => s - 1);
  };

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    
    // Step 0 -> Step 1
    if (step === 0) {
      if (formData.firstName.trim() && formData.lastName.trim()) {
        setError("");
        setStep(1);
      } else {
        setError("Veuillez renseigner votre nom et prénom.");
      }
      return;
    }

    // Step 1 -> Step 2
    if (step === 1) {
      if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
        setError("");
        setStep(2);
      } else {
        setError("Veuillez entrer une adresse email valide.");
      }
      return;
    }
    
    // Final Step (2) -> API Call
    if (step === 2) {
      if (formData.password.length < 8) {
        setError("Le mot de passe doit faire au moins 8 caractères.");
        return;
      }
      
      if (formData.password !== formData.confirmPassword) {
        setError("Les mots de passe ne correspondent pas.");
        return;
      }

      setError("");
      setLoading(true);
      try {
        // 1. Register the account
        await api.auth.register(formData.email, formData.password, "student");
        
        // 2. Automatically login
        const { access_token, refresh_token } = await api.auth.login(formData.email, formData.password);
        
        // 3. Store tokens
        tokenStore.setTokens(access_token, refresh_token);
        
        // 4. Redirect to dashboard
        router.push("/chat");
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden relative">
        
        {/* Progress Bar Animation */}
        <div className="absolute top-0 left-0 w-full h-1 bg-slate-100 z-50">
          <div 
            className="h-full bg-brand transition-all duration-700 ease-[cubic-bezier(0.34,1.56,0.64,1)] shadow-[0_0_10px_rgba(var(--brand-rgb),0.5)]"
            style={{ width: `${((step + 1) / 3) * 100}%` }}
          />
        </div>

        <div className="p-8">
          {/* Header */}
          <div className="mb-10 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand/5 text-brand mb-4">
              <GraduationCap size={32} />
            </div>
            <h1 className="text-3xl font-serif font-bold text-slate-900">
              n7<span className="text-brand">chat</span>
            </h1>
            <p className="mt-2 text-sm text-slate-500 font-medium">
              {step === 0 && "Commençons par faire connaissance"}
              {step === 1 && "Quelle est votre adresse mail ?"}
              {step === 2 && "Sécurisez votre compte étudiant"}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="relative overflow-hidden">
            {/* Step Container (Swipe Effect) */}
            <div 
              className="flex transition-transform duration-700 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
              style={{ transform: `translateX(-${step * 100}%)` }}
            >
              {/* Step 0: Names */}
              <div className="w-full shrink-0 space-y-4 px-1">
                <div className="space-y-4">
                  <div className="relative group">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-brand transition-colors" size={18} />
                    <input
                      type="text"
                      placeholder="Prénom"
                      value={formData.firstName}
                      onChange={(e) => setFormData({...formData, firstName: e.target.value})}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-10 pr-4 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand/5 transition-all"
                    />
                  </div>
                  <div className="relative group">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-brand transition-colors" size={18} />
                    <input
                      type="text"
                      placeholder="Nom de famille"
                      value={formData.lastName}
                      onChange={(e) => setFormData({...formData, lastName: e.target.value})}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-10 pr-4 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand/5 transition-all"
                    />
                  </div>
                </div>
              </div>

              {/* Step 1: Email */}
              <div className="w-full shrink-0 px-1">
                <div className="relative group">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-brand transition-colors" size={18} />
                  <input
                    type="email"
                    placeholder="votre.email@ecole.com"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-10 pr-4 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand/5 transition-all"
                  />
                </div>
                <p className="mt-3 text-[10px] text-slate-400 text-center uppercase tracking-widest font-bold">
                  Utilisez votre adresse institutionnelle
                </p>
              </div>

              {/* Step 2: Password */}
              <div className="w-full shrink-0 px-1 space-y-4">
                <div className="relative group">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-brand transition-colors" size={18} />
                  <input
                    type="password"
                    placeholder="Créer un mot de passe"
                    minLength={8}
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-10 pr-4 text-sm outline-none focus:border-brand focus:ring-4 focus:ring-brand/5 transition-all"
                  />
                </div>
                <div className="relative group">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-brand transition-colors" size={18} />
                  <input
                    type="password"
                    placeholder="Confirmer le mot de passe"
                    minLength={8}
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
                    className={`w-full bg-slate-50 border rounded-xl py-3 pl-10 pr-4 text-sm outline-none transition-all ${
                      formData.confirmPassword && formData.password !== formData.confirmPassword 
                        ? 'border-red-300 focus:ring-red-500/5' 
                        : 'border-slate-200 focus:border-brand focus:ring-brand/5'
                    }`}
                  />
                </div>
                <div className="flex items-center gap-2 px-1">
                  <div className={`h-1 flex-1 rounded-full ${formData.password.length >= 8 ? 'bg-green-500' : 'bg-slate-200'}`} />
                  <div className={`h-1 flex-1 rounded-full ${formData.password.length >= 10 ? 'bg-green-500' : 'bg-slate-200'}`} />
                  <div className={`h-1 flex-1 rounded-full ${formData.password.length >= 12 ? 'bg-green-500' : 'bg-slate-200'}`} />
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
                {loading ? "Chargement..." : step === 2 ? "Créer mon compte" : "Suivant"}
                {step < 2 && <ArrowRight size={18} />}
                {step === 2 && !loading && <CheckCircle2 size={18} />}
              </button>
            </div>
          </form>

          <p className="mt-8 text-center text-xs text-slate-400">
            Déjà un compte ?{" "}
            <a href="/login" className="text-brand font-bold hover:underline">Se connecter</a>
          </p>
        </div>
      </div>
    </main>
  );
}

