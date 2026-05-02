/**
 * app/(dashboard)/courses/page.tsx
 * Course listing page — admins see CRUD controls. Light academic theme.
 */
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { tokenStore, getUserRole } from "@/lib/auth";
import { Book, GraduationCap, ChevronRight, Loader2, Plus, Target, Sparkles } from "lucide-react";

type Course = { id: string; title: string; description?: string };

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [recommended, setRecommended] = useState<Course[]>([]);
  const [role, setRole] = useState<"student" | "admin">("student");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = tokenStore.getAccess() ?? "";
    setRole(getUserRole(token) ?? "student");
    
    Promise.all([
      api.courses.list(token),
      api.courses.recommendations(token)
    ])
      .then(([resList, resRecs]) => {
        setCourses(resList.courses as Course[]);
        setRecommended(resRecs.recommendations as Course[]);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 bg-white min-h-screen text-slate-900">
      <div className="max-w-6xl mx-auto">
        <header className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-3xl font-serif font-bold text-slate-900 mb-2">Catalogue des Cours</h1>
            <p className="text-slate-500">Accédez à vos modules d&apos;enseignement et ressources pédagogiques.</p>
          </div>
          {role === "admin" && (
            <button
              id="add-course-btn"
              className="flex items-center gap-2 rounded-xl bg-brand px-5 py-2.5 text-sm font-bold text-white hover:bg-brand-hover transition-all shadow-lg shadow-brand/10 active:scale-95"
            >
              <Plus size={18} /> Nouveau Module
            </button>
          )}
        </header>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 opacity-40">
            <Loader2 className="animate-spin text-brand mb-4" size={40} />
            <p className="font-medium">Préparation de votre parcours...</p>
          </div>
        ) : (
          <>
            {/* Recommendations Section */}
            {recommended.length > 0 && (
              <section className="mb-16">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2 rounded-xl bg-amber-50 text-amber-600">
                    <Target size={24} />
                  </div>
                  <div>
                    <h2 className="text-xl font-serif font-bold text-slate-900 flex items-center gap-2">
                      Recommandé pour vous <Sparkles size={16} className="text-amber-400" />
                    </h2>
                    <p className="text-xs text-slate-400 font-medium">Basé sur votre profil académique</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {recommended.map((c) => (
                    <div key={c.id} className="relative group cursor-pointer">
                      <div className="absolute inset-0 bg-gradient-to-br from-amber-100/20 to-brand/5 rounded-2xl -m-1 blur-sm group-hover:blur-md transition-all opacity-0 group-hover:opacity-100" />
                      <div className="relative bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:border-amber-200 hover:shadow-lg transition-all overflow-hidden">
                        <div className="flex items-start justify-between mb-3">
                          <h3 className="font-bold text-slate-900 text-sm group-hover:text-amber-700 transition-colors">{c.title}</h3>
                          <ChevronRight size={16} className="text-slate-300 group-hover:text-amber-500 group-hover:translate-x-1 transition-all" />
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded uppercase tracking-widest">Premium</span>
                          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Niveau L3</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Main Catalogue */}
            <div className="flex items-center gap-2 mb-8">
              <div className="h-px bg-slate-200 flex-1" />
              <h2 className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.3em]">Tous les modules</h2>
              <div className="h-px bg-slate-200 flex-1" />
            </div>

            {courses.length === 0 ? (
              <div className="text-center py-20 bg-slate-50 rounded-3xl border border-dashed border-slate-200">
                <p className="text-slate-400 font-medium italic">Aucun cours disponible pour le moment.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {courses.map((c) => (
                  <div
                    key={c.id}
                    className="group flex flex-col rounded-2xl border border-slate-200 bg-white shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden"
                  >
                    <div className="h-3 bg-brand/10 group-hover:bg-brand transition-colors" />
                    <div className="p-6 flex flex-col flex-1">
                      <div className="flex items-center justify-between mb-4">
                        <span className="p-2 rounded-lg bg-red-50 text-brand">
                          <Book size={24} />
                        </span>
                        <span className="text-[10px] font-bold text-brand uppercase tracking-widest bg-red-50 px-2 py-1 rounded">
                          CORE-MOD
                        </span>
                      </div>
                      <h3 className="text-lg font-serif font-bold text-slate-900 mb-2 group-hover:text-brand transition-colors">
                        {c.title}
                      </h3>
                      <p className="text-sm text-slate-500 line-clamp-2 mb-6">
                        {c.description || "Aucune description disponible."}
                      </p>
                      <div className="mt-auto pt-4 border-t border-slate-50 flex items-center justify-between">
                        {role === "admin" ? (
                          <div className="flex gap-2">
                            <button className="text-xs font-bold text-brand hover:underline">
                              Modifier
                            </button>
                            <button className="text-xs font-bold text-red-600 hover:underline">
                              Supprimer
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 text-xs font-medium text-slate-400">
                            <GraduationCap size={14} /> Niveau: Master
                          </div>
                        )}
                        <button className="flex items-center gap-1 text-sm font-bold text-brand hover:underline ml-auto">
                          Détails <ChevronRight size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
