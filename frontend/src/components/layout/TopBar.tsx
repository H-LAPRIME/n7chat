"use client";
/* eslint-disable @next/next/no-img-element */

import { useAuth } from "@/context/AuthContext";
import { getApiUrl } from "@/lib/api";
import { LogOut, User as UserIcon } from "lucide-react";
import { usePathname } from "next/navigation";
import { useState } from "react";

export default function TopBar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [logoFailed, setLogoFailed] = useState(false);
  const logoUrl = `${getApiUrl()}/profile/assets/logo_enset.png`;

  const getPageTitle = () => {
    if (pathname.includes("/chat")) return "Chat Assistant";
    if (pathname.includes("/courses")) return "Courses Directory";
    if (pathname.includes("/events")) return "University Events";
    if (pathname.includes("/admin")) return "Admin Management";
    if (pathname.includes("/documents")) return "Admin Documents";
    if (pathname.includes("/profile")) return "Account Profile";
    return "Dashboard";
  };

  return (
    <header className="h-16 bg-white border-b border-border flex items-center justify-between px-6 shrink-0 shadow-sm z-10">
      <div className="flex items-center gap-3 min-w-0">
        <h2 className="text-xl font-bold tracking-tight text-text truncate">{getPageTitle()}</h2>
        {!logoFailed && (
          <div className="hidden sm:flex h-12 w-12 items-center justify-center overflow-hidden">
            <img
              src={logoUrl}
              alt="ENSET logo"
              className="h-full w-full object-contain"
              onError={() => setLogoFailed(true)}
            />
          </div>
        )}
      </div>
      
      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-3">
            <div className="text-right hidden md:block">
              <p className="text-sm font-semibold text-text leading-tight">
                {user.first_name || "Welcome"}, {user.last_name || user.email.split("@")[0]}
              </p>
              <p className="text-xs text-text-muted capitalize">{user.role}</p>
            </div>
            <div className="w-10 h-10 rounded-full bg-primary-light flex items-center justify-center text-primary border border-primary/20 shadow-sm overflow-hidden">
              {user.photo_url ? (
                <img src={user.photo_url} alt="Profile photo" className="h-full w-full object-cover" />
              ) : (
                <UserIcon size={20} />
              )}
            </div>
          </div>
        )}
        
        <div className="w-px h-8 bg-border mx-1"></div>
        
        <button 
          onClick={logout}
          className="text-text-muted hover:text-danger hover:bg-danger/10 p-2 rounded-lg transition-colors"
          title="Sign out"
        >
          <LogOut size={20} />
        </button>
      </div>
    </header>
  );
}
