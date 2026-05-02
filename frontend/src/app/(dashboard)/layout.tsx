/**
 * app/(dashboard)/layout.tsx
 * Wraps all dashboard pages with the sidebar and a top header.
 */
"use client";

import { ReactNode, useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import NotificationBell from "@/components/NotificationBell";
import { Search, LogOut, User as UserIcon, ChevronDown, Settings } from "lucide-react";
import { tokenStore, getUserRole } from "@/lib/auth";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<string>("Étudiant");
  const [name, setName] = useState<string>("Utilisateur n7");
  const [avatar, setAvatar] = useState<string>("");
  const [showDropdown, setShowDropdown] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const token = tokenStore.getAccess();
    if (token) {
      const r = getUserRole(token);
      setRole(r === "admin" ? "Enseignant" : "Étudiant");
      
      // Fetch user profile to get info
      api.auth.me(token)
        .then(u => {
          setName(u.name);
          setAvatar(u.avatar);
        })
        .catch(console.error);
    }
  }, []);

  const handleLogout = () => {
    tokenStore.clear();
    router.push("/login");
  };

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      <Sidebar />
      
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-16 border-b border-slate-100 bg-white/80 backdrop-blur-md z-30 flex items-center justify-between px-8 shrink-0">
          <div className="flex items-center gap-4 flex-1">
            <div className="relative max-w-md w-full group hidden md:block">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-brand transition-colors" size={18} />
              <input 
                type="text" 
                placeholder="Rechercher un cours, un document..." 
                className="w-full bg-slate-50 border-none rounded-xl py-2 pl-10 pr-4 text-sm focus:ring-2 focus:ring-brand/20 transition-all outline-none"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <NotificationBell />
            <div className="h-8 w-px bg-slate-100 mx-2" />
            
            {/* Profile Dropdown Trigger */}
            <div className="relative">
              <button 
                onClick={() => setShowDropdown(!showDropdown)}
                className="flex items-center gap-3 pl-2 group cursor-pointer hover:bg-slate-50 rounded-xl p-1.5 transition-all"
              >
                <div className="text-right hidden sm:block">
                  <p className="text-xs font-bold text-slate-900 leading-none">{name}</p>
                  <p className="text-[10px] text-slate-400 font-medium mt-1 uppercase tracking-wider">{role}</p>
                </div>
                <div className="w-9 h-9 rounded-full border border-slate-200 overflow-hidden bg-white flex items-center justify-center shadow-sm group-hover:border-brand/40 transition-colors">
                  <img 
                    src={avatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=0F172A&color=fff`} 
                    alt="Profile"
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=0F172A&color=fff`;
                    }}
                  />
                </div>
                <ChevronDown size={14} className={`text-slate-400 transition-transform duration-200 ${showDropdown ? "rotate-180" : ""}`} />
              </button>

              {/* Dropdown Menu */}
              {showDropdown && (
                <>
                  <div 
                    className="fixed inset-0 z-40" 
                    onClick={() => setShowDropdown(false)}
                  />
                  <div className="absolute right-0 mt-2 w-56 bg-white rounded-2xl shadow-2xl border border-slate-100 py-2 z-50 animate-in fade-in zoom-in duration-200 origin-top-right">
                    <div className="px-4 py-3 border-b border-slate-50 mb-1">
                      <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Mon Compte</p>
                    </div>
                    <button 
                      onClick={() => {
                        router.push("/profile");
                        setShowDropdown(false);
                      }}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 hover:text-brand transition-colors text-left"
                    >
                      <UserIcon size={18} />
                      Consulter profil
                    </button>
                    <button 
                      onClick={() => {
                        router.push("/settings");
                        setShowDropdown(false);
                      }}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 hover:text-brand transition-colors text-left"
                    >
                      <Settings size={18} />
                      Paramètres
                    </button>
                    <div className="h-px bg-slate-50 my-1" />
                    <button 
                      onClick={handleLogout}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors text-left font-medium"
                    >
                      <LogOut size={18} />
                      Déconnexion
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto bg-white">
          {children}
        </main>
      </div>
    </div>
  );
}
