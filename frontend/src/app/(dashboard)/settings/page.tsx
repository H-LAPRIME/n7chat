"""
app/(dashboard)/settings/page.tsx
User settings — language selector, logout.
"""
"use client";

import { useRouter } from "next/navigation";
import { tokenStore } from "@/lib/auth";
import { api } from "@/lib/api";

const LOCALES = [
  { code: "fr", label: "🇫🇷 Français" },
  { code: "ar", label: "🇸🇦 العربية" },
  { code: "ma", label: "🇲🇦 Darija" },
  { code: "en", label: "🇬🇧 English" },
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
    <main className="min-h-screen bg-[#0f0f1a] text-white p-8">
      <div className="max-w-lg mx-auto">
        <h1 className="text-2xl font-bold mb-8">
          ⚙️ <span className="text-white/70">Paramètres</span>
        </h1>

        {/* Language */}
        <section className="rounded-2xl border border-white/10 bg-white/5 p-6 mb-4">
          <h2 className="font-semibold mb-4 text-white/80">🌍 Langue</h2>
          <div className="grid grid-cols-2 gap-2">
            {LOCALES.map((l) => (
              <button
                key={l.code}
                id={`locale-${l.code}`}
                className="rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-sm hover:border-[#6C5CE7]/60 hover:text-white transition-colors text-white/60"
              >
                {l.label}
              </button>
            ))}
          </div>
        </section>

        {/* Logout */}
        <section className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="font-semibold mb-4 text-white/80">🔐 Compte</h2>
          <button
            id="logout-btn"
            onClick={handleLogout}
            className="rounded-lg bg-[#D63031]/80 px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#D63031] transition-colors"
          >
            Se déconnecter
          </button>
        </section>
      </div>
    </main>
  );
}
