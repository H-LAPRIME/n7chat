"use client";
/* eslint-disable @next/next/no-img-element */

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { getApiUrl } from "@/lib/api";
import { useRouter } from "next/navigation";
import { GraduationCap, ArrowRight, Loader2 } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [logoFailed, setLogoFailed] = useState(false);
  const { login } = useAuth();
  const router = useRouter();
  const logoUrl = `${getApiUrl()}/profile/assets/logo_enset.png`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(email, password);
      router.push("/dashboard/chat");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to login. Check your credentials.";
      setError(message);
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-surface-2">
      <div className="hidden lg:flex w-1/2 bg-primary relative overflow-hidden flex-col items-center justify-center p-12 text-white">
        <div className="absolute inset-0 bg-gradient-to-br from-primary-dark via-primary to-accent opacity-90"></div>
        <div className="absolute inset-0 opacity-20" style={{ backgroundImage: "linear-gradient(#ffffff 1px, transparent 1px), linear-gradient(90deg, #ffffff 1px, transparent 1px)", backgroundSize: "40px 40px" }}></div>
        <div className="relative z-10 flex flex-col items-center text-center max-w-lg">
          <div className="w-24 h-24 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur-md mb-8 border border-white/30 shadow-2xl">
            <GraduationCap size={48} className="text-white" />
          </div>
          <h1 className="text-5xl font-bold mb-6 tracking-tight">N7Chat Platform</h1>
          <p className="text-xl text-primary-light font-light leading-relaxed">
            Your intelligent academic assistant. Access your courses, manage events, and explore dynamic learning.
          </p>
        </div>
      </div>

      <div className="flex-1 flex flex-col justify-center items-center px-6 lg:px-16 w-full">
        <div className="w-full max-w-md bg-white p-8 sm:p-10 rounded-2xl shadow-md border border-border/50">
          <div className="mb-7 flex justify-center lg:justify-start">
            <div className="h-24 w-24 flex items-center justify-center overflow-hidden">
              {!logoFailed ? (
                <img
                  src={logoUrl}
                  alt="ENSET logo"
                  className="h-full w-full object-contain"
                  onError={() => setLogoFailed(true)}
                />
              ) : (
                <GraduationCap size={32} className="text-primary" />
              )}
            </div>
          </div>
          <div className="mb-8 text-center lg:text-left">
            <h2 className="text-3xl font-bold text-text mb-2 tracking-tight">Welcome Back</h2>
            <p className="text-text-muted">Sign in to your academic account</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="p-4 rounded-lg bg-danger/10 border border-danger/20 text-danger text-sm font-medium">
                {error}
              </div>
            )}
            
            <div className="space-y-2">
              <label className="text-sm font-semibold text-text-muted select-none">Email Address</label>
              <input
                type="email"
                required
                className="input-field py-3 bg-surface-2/50"
                placeholder="student@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-semibold text-text-muted select-none">Password</label>
              <input
                type="password"
                required
                className="input-field py-3 bg-surface-2/50"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            
            <button
              type="submit"
              disabled={isSubmitting || !email || !password}
              className="w-full btn-primary py-3 mt-6 flex justify-center items-center gap-2 shadow-sm text-lg"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  Signing in...
                </>
              ) : (
                <>
                  Sign In
                  <ArrowRight size={20} className="opacity-80" />
                </>
              )}
            </button>
          </form>
          
          <div className="mt-8 pt-6 border-t border-border/50 text-center">
             <p className="text-sm text-text-muted">
               Demo accounts typically use <span className="font-medium text-text">dev-admin</span> or a plain text password in dev environments.
             </p>
          </div>
        </div>
      </div>
    </div>
  );
}
