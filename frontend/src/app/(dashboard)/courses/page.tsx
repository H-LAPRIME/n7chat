/**
 * app/(dashboard)/courses/page.tsx
 * Course listing page — admins see CRUD controls.
 */
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { tokenStore, getUserRole } from "@/lib/auth";

type Course = { id: string; title: string; description: string };

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [role, setRole] = useState<"student" | "admin">("student");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = tokenStore.getAccess() ?? "";
    setRole(getUserRole(token) ?? "student");
    api.courses
      .list(token)
      .then((res) => setCourses(res.courses as Course[]))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="min-h-screen bg-[#0f0f1a] text-white p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold">
            📚 <span className="text-[#6C5CE7]">Cours</span>
          </h1>
          {role === "admin" && (
            <button
              id="add-course-btn"
              className="rounded-lg bg-[#6C5CE7] px-4 py-2 text-sm font-semibold hover:bg-[#5a4bd1] transition-colors"
            >
              + Ajouter un cours
            </button>
          )}
        </div>

        {loading ? (
          <p className="text-white/40">Chargement…</p>
        ) : courses.length === 0 ? (
          <p className="text-white/40">Aucun cours disponible pour le moment.</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {courses.map((c) => (
              <div
                key={c.id}
                className="rounded-2xl border border-white/10 bg-white/5 p-5 hover:border-[#6C5CE7]/40 transition-colors"
              >
                <h2 className="font-semibold text-white mb-1">{c.title}</h2>
                <p className="text-sm text-white/50">{c.description}</p>
                {role === "admin" && (
                  <div className="mt-3 flex gap-2">
                    <button className="text-xs text-[#FDCB6E] hover:underline">
                      Modifier
                    </button>
                    <button className="text-xs text-[#D63031] hover:underline">
                      Supprimer
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
