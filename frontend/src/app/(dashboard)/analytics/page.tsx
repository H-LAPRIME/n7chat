/**
 * app/(dashboard)/analytics/page.tsx
 * Analytics dashboard — admin only.
 */
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { tokenStore } from "@/lib/auth";

type AnalyticsData = {
  top_questions: string[];
  user_activity: { today: number; week: number };
  errors: { count: number; last: string | null };
};

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = tokenStore.getAccess() ?? "";
    api.analytics.get(token).then(setData).catch((e) => setError(e.message));
  }, []);

  if (error)
    return (
      <main className="min-h-screen bg-[#0f0f1a] text-white flex items-center justify-center">
        <p className="text-[#D63031]">❌ {error}</p>
      </main>
    );

  return (
    <main className="min-h-screen bg-[#0f0f1a] text-white p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-8">
          📊 <span className="text-[#FDCB6E]">Analytics</span>
        </h1>

        {/* Activity cards */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
            <p className="text-xs text-white/40 uppercase tracking-wider mb-1">Aujourd&apos;hui</p>
            <p className="text-4xl font-bold text-[#00B894]">
              {data?.user_activity.today ?? "—"}
            </p>
            <p className="text-sm text-white/40 mt-1">utilisateurs actifs</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
            <p className="text-xs text-white/40 uppercase tracking-wider mb-1">Cette semaine</p>
            <p className="text-4xl font-bold text-[#6C5CE7]">
              {data?.user_activity.week ?? "—"}
            </p>
            <p className="text-sm text-white/40 mt-1">utilisateurs actifs</p>
          </div>
        </div>

        {/* Top questions */}
        <div className="rounded-2xl border border-white/10 bg-white/5 p-5 mb-4">
          <h2 className="font-semibold mb-3 text-white/80">🔥 Questions populaires</h2>
          {data?.top_questions.length ? (
            <ol className="space-y-2">
              {data.top_questions.map((q, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-white/60">
                  <span className="text-[#FDCB6E] font-bold w-5 shrink-0">{i + 1}.</span>
                  {q}
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-white/30">Aucune donnée disponible.</p>
          )}
        </div>

        {/* Errors */}
        <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
          <h2 className="font-semibold mb-3 text-white/80">⚠️ Erreurs</h2>
          <p className="text-sm text-white/60">
            Total : <span className="text-[#D63031] font-semibold">{data?.errors.count ?? 0}</span>
            {data?.errors.last && ` — Dernière : ${data.errors.last}`}
          </p>
        </div>
      </div>
    </main>
  );
}
