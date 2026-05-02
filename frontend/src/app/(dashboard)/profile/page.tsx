/**
 * app/(dashboard)/profile/page.tsx
 * User profile page with premium academic aesthetic.
 */
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { tokenStore } from "@/lib/auth";
import { 
  User, 
  Mail, 
  Shield, 
  BookOpen, 
  Calendar, 
  MapPin, 
  Camera,
  Edit3,
  CheckCircle2,
  Settings,
  GraduationCap
} from "lucide-react";

type UserProfile = {
  id: string;
  email: string;
  role: string;
  name: string;
  bio: string;
  avatar: string;
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = tokenStore.getAccess();
    if (token) {
      api.auth.me(token)
        .then(setProfile)
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-10 h-10 border-4 border-slate-100 border-t-brand rounded-full animate-spin" />
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="h-full bg-white overflow-y-auto scrollbar-thin scrollbar-thumb-slate-200">
      {/* Premium Header Backdrop */}
      <div className="relative h-64 bg-slate-900 overflow-hidden">
        <div className="absolute inset-0 opacity-20" style={{ 
          backgroundImage: "radial-gradient(#fff 1px, transparent 1px)", 
          backgroundSize: "20px 20px" 
        }} />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-slate-900/50" />
      </div>

      <div className="max-w-5xl mx-auto px-8 -mt-32 relative z-10 pb-20">
        <div className="flex flex-col md:flex-row gap-8 items-start">
          {/* Left Column: Avatar & Quick Info */}
          <div className="w-full md:w-80 shrink-0">
            <div className="bg-white rounded-3xl p-6 shadow-xl border border-slate-100">
              <div className="relative mx-auto w-32 h-32 mb-6">
                <div className="w-full h-full rounded-full border-4 border-white shadow-lg overflow-hidden bg-slate-50">
                  <img 
                    src={profile.avatar} 
                    alt={profile.name} 
                    className="w-full h-full object-cover" 
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = `https://ui-avatars.com/api/?name=${encodeURIComponent(profile.name)}&background=0F172A&color=fff`;
                    }}
                  />
                </div>
                <button className="absolute bottom-0 right-0 p-2 bg-brand text-white rounded-full shadow-lg hover:scale-110 transition-transform active:scale-95">
                  <Camera size={16} />
                </button>
              </div>

              <div className="text-center mb-6">
                <h1 className="text-2xl font-serif font-bold text-slate-900">{profile.name}</h1>
                <p className="text-sm font-bold text-brand uppercase tracking-widest mt-1">
                  {profile.role === "admin" ? "Enseignant" : "Étudiant"}
                </p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-3 text-slate-600">
                  <div className="p-2 bg-slate-50 rounded-lg text-slate-400">
                    <Mail size={16} />
                  </div>
                  <span className="text-sm truncate">{profile.email}</span>
                </div>
                <div className="flex items-center gap-3 text-slate-600">
                  <div className="p-2 bg-slate-50 rounded-lg text-slate-400">
                    <GraduationCap size={16} />
                  </div>
                  <span className="text-sm">N7 • ENSEEIHT</span>
                </div>
                <div className="flex items-center gap-3 text-slate-600">
                  <div className="p-2 bg-slate-50 rounded-lg text-slate-400">
                    <MapPin size={16} />
                  </div>
                  <span className="text-sm">Toulouse, France</span>
                </div>
              </div>

              <button className="w-full mt-8 py-3 rounded-xl bg-slate-900 text-white font-bold text-sm hover:bg-slate-800 transition-all active:scale-[0.98] flex items-center justify-center gap-2 shadow-lg shadow-slate-200">
                <Edit3 size={16} /> Éditer le profil
              </button>
            </div>

            {/* Verification Badge */}
            <div className="mt-6 bg-brand/5 border border-brand/10 rounded-2xl p-4 flex items-center gap-3">
              <CheckCircle2 className="text-brand" size={24} />
              <div>
                <p className="text-xs font-bold text-brand uppercase tracking-wider">Compte Vérifié</p>
                <p className="text-[10px] text-slate-500 font-medium">Statut académique confirmé</p>
              </div>
            </div>
          </div>

          {/* Right Column: Detailed Info & Params */}
          <div className="flex-1 space-y-6">
            {/* Bio Section */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-slate-100">
              <h2 className="text-lg font-serif font-bold text-slate-900 mb-4 flex items-center gap-2">
                <BookOpen className="text-brand" size={20} /> À propos
              </h2>
              <p className="text-slate-600 leading-relaxed italic">
                "{profile.bio}"
              </p>
            </div>

            {/* Dashboard Sections */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="bg-white rounded-3xl p-6 shadow-sm border border-slate-100 group hover:border-brand/20 transition-colors">
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-blue-50 text-blue-600 rounded-xl group-hover:scale-110 transition-transform">
                    <Shield size={20} />
                  </div>
                  <button className="text-slate-400 hover:text-brand transition-colors">
                    <Settings size={18} />
                  </button>
                </div>
                <h3 className="font-bold text-slate-900 mb-1">Sécurité</h3>
                <p className="text-xs text-slate-500">Gérez vos mots de passe et l&apos;authentification à deux facteurs.</p>
              </div>

              <div className="bg-white rounded-3xl p-6 shadow-sm border border-slate-100 group hover:border-brand/20 transition-colors">
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-purple-50 text-purple-600 rounded-xl group-hover:scale-110 transition-transform">
                    <Calendar size={20} />
                  </div>
                  <button className="text-slate-400 hover:text-brand transition-colors">
                    <Settings size={18} />
                  </button>
                </div>
                <h3 className="font-bold text-slate-900 mb-1">Activité</h3>
                <p className="text-xs text-slate-500">Historique de vos interactions avec l&apos;assistant académique.</p>
              </div>
            </div>

            {/* Account Details Form-like view */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-slate-100">
              <h2 className="text-lg font-serif font-bold text-slate-900 mb-6">Paramètres du Compte</h2>
              <div className="space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between py-4 border-b border-slate-50">
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Email Principal</p>
                    <p className="text-sm font-medium text-slate-700 mt-1">{profile.email}</p>
                  </div>
                  <button className="text-xs font-bold text-brand mt-2 sm:mt-0 px-4 py-2 rounded-lg bg-brand/5 hover:bg-brand/10 transition-colors">
                    Changer
                  </button>
                </div>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between py-4 border-b border-slate-50">
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Mot de passe</p>
                    <p className="text-sm font-medium text-slate-700 mt-1">••••••••••••</p>
                  </div>
                  <button className="text-xs font-bold text-brand mt-2 sm:mt-0 px-4 py-2 rounded-lg bg-brand/5 hover:bg-brand/10 transition-colors">
                    Modifier
                  </button>
                </div>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between py-4">
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Session</p>
                    <p className="text-sm font-medium text-slate-700 mt-1">ID: {profile.id.slice(0, 8)}...</p>
                  </div>
                  <span className="text-[10px] bg-green-50 text-green-600 px-3 py-1 rounded-full font-bold">ACTIF</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
