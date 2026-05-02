/**
 * app/(dashboard)/settings/page.tsx
 * User settings — language selector, logout.
 */
"use client";

import { useRouter } from "next/navigation";
import { tokenStore } from "@/lib/auth";
import { api } from "@/lib/api";
import { 
  Globe, 
  LogOut, 
  User, 
  ShieldAlert,
  ChevronRight,
  Info
} from "lucide-react";

const LOCALES = [
  { code: "fr", label: "Français" },
  { code: "en", label: "English" },
  { code: "ar", label: "العربية" },
];

export default function SettingsPage() {
  const router = useRouter();

  async function handleLogout() {
    const token = tokenStore.getAccess() ?? "";
    try {
      await api.auth.logout(token);
    } catch {
      /* ignore */
    }
    tokenStore.clear();
    router.push("/login");
  }

  return (
    <div className="p-8 bg-white h-full text-slate-900">
      <div className="max-w-2xl mx-auto">
        <header className="mb-10">
          <h1 className="text-3xl font-serif font-bold text-slate-900 mb-2">Paramètres</h1>
          <p className="text-slate-500">Gérez vos préférences et votre compte n7chat.</p>
        </header>

        <div className="space-y-6">
          <section className="p-6 rounded-2xl border border-slate-200 bg-white shadow-sm">
            <h2 className="text-lg font-serif font-bold mb-6 flex items-center gap-2">
              <User className="text-brand" size={20} /> Profil Utilisateur
            </h2>
            <div className="space-y-6">
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-2">
                  Langue de l&apos;interface
                </label>
                <div className="relative group">
                  <Globe className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-brand transition-colors" size={18} />
                  <select className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-12 pr-4 py-3 text-sm text-slate-900 outline-none focus:border-brand focus:ring-4 focus:ring-brand/5 transition-all appearance-none cursor-pointer">
                    {LOCALES.map(l => (
                      <option key={l.code}>{l.label}</option>
                    ))}
                  </select>
                  <ChevronRight className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 rotate-90" size={16} />
                </div>
              </div>
            </div>
          </section>

          <section className="p-6 rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden relative">
            <div className="absolute top-0 right-0 p-4 opacity-[0.03] pointer-events-none">
              <ShieldAlert size={120} />
            </div>
            <h2 className="text-lg font-serif font-bold mb-4 text-red-600 flex items-center gap-2">
              <ShieldAlert size={20} /> Zone de danger
            </h2>
            <p className="text-sm text-slate-500 mb-6 leading-relaxed">
              La déconnexion mettra fin à votre session sécurisée. Vous devrez vous authentifier à nouveau pour accéder à l&apos;assistant IA et vos documents.
            </p>
            <button
              onClick={handleLogout}
              className="w-full py-4 rounded-xl bg-white border border-red-200 text-red-600 font-bold text-sm hover:bg-red-50 hover:border-red-300 transition-all active:scale-[0.98] flex items-center justify-center gap-2"
            >
              <LogOut size={18} /> Déconnexion de la plateforme
            </button>
          </section>
        </div>

        <div className="mt-12 flex flex-col items-center gap-2 opacity-30">
          <Info size={16} />
          <p className="text-center text-[10px] font-bold tracking-[0.3em] uppercase">
            n7chat v1.0.0 — Excellence Académique
          </p>
        </div>
      </div>
    </div>
  );
}
