/**
 * app/(dashboard)/analytics/analytics-page.tsx
 * Analytics dashboard — admin only. Light academic theme.
 */
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { tokenStore } from "@/lib/auth";
import { Users, AlertTriangle, TrendingUp, Search, Calendar } from "lucide-react";

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
      <main className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="bg-white border border-red-100 p-6 rounded-2xl shadow-sm text-center">
          <p className="text-red-600 font-medium"> {error}</p>
        </div>
      </main>
    );

  return (
    <div className="p-8 bg-white h-full text-slate-900">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-serif font-bold text-slate-900 mb-2">Analytique</h1>
        <p className="text-slate-500 mb-8">Aperçu de l&apos;activité de la plateforme et maintenance du système.</p>

        {/* Real Data Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md transition group">
            <div className="flex items-center justify-between mb-4">
              <span className="p-3 rounded-xl bg-blue-50 text-blue-600">
                <Users size={24} />
              </span>
              <div className="flex items-center gap-1 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                <Calendar size={12} /> Utilisateurs
              </div>
            </div>
            <div className="flex items-end gap-4">
              <div>
                <h3 className="text-sm font-medium text-slate-500 mb-1">Aujourd&apos;hui</h3>
                <p className="text-3xl font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                  {data?.user_activity.today ?? "—"}
                </p>
              </div>
              <div className="h-10 w-px bg-slate-100" />
              <div>
                <h3 className="text-sm font-medium text-slate-500 mb-1">Cette Semaine</h3>
                <p className="text-3xl font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                  {data?.user_activity.week ?? "—"}
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md transition group">
            <div className="flex items-center justify-between mb-4">
              <span className="p-3 rounded-xl bg-red-50 text-red-600">
                <AlertTriangle size={24} />
              </span>
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Système</div>
            </div>
            <h3 className="text-sm font-medium text-slate-500 mb-1">Erreurs Détectées</h3>
            <p className="text-3xl font-bold text-red-600">
              {data?.errors.count ?? 0}
            </p>
            {data?.errors.last && (
              <p className="mt-2 text-xs text-slate-400 italic truncate">
                Dernière: {data.errors.last}
              </p>
            )}
          </div>
        </div>

        {/* Questions populaires */}
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm mb-8">
          <h2 className="text-xl font-serif font-bold mb-6 flex items-center gap-2">
            <TrendingUp className="text-brand" size={24} /> Questions populaires
          </h2>
          {data?.top_questions.length ? (
            <div className="grid grid-cols-1 gap-3">
              {data.top_questions.map((q, i) => (
                <div key={i} className="flex items-center gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100 hover:border-brand/20 transition-colors group/item">
                  <span className="text-lg font-serif font-bold text-brand w-6">{i + 1}</span>
                  <p className="text-sm text-slate-700 font-medium flex-1">{q}</p>
                  <Search size={16} className="text-slate-300 group-hover/item:text-brand transition-colors" />
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center text-slate-400 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
              <p className="text-sm italic">Aucune question enregistrée pour le moment.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
