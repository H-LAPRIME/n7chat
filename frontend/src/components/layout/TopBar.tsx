"use client";

import { useAuth } from "@/context/AuthContext";
import { LogOut, User as UserIcon } from "lucide-react";
import { usePathname } from "next/navigation";

export default function TopBar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

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
      <h2 className="text-xl font-bold tracking-tight text-text">{getPageTitle()}</h2>
      
      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-3">
            <div className="text-right hidden md:block">
              <p className="text-sm font-semibold text-text leading-tight">
                {user.first_name || "Welcome"}, {user.last_name || user.email.split("@")[0]}
              </p>
              <p className="text-xs text-text-muted capitalize">{user.role}</p>
            </div>
            <div className="w-10 h-10 rounded-full bg-primary-light flex items-center justify-center text-primary border border-primary/20 shadow-sm">
              <UserIcon size={20} />
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
