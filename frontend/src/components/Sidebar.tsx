/**
 * components/Sidebar.tsx
 * Collapsible role-aware navigation sidebar.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { tokenStore, getUserRole } from "@/lib/auth";
import NotificationBell from "./NotificationBell";

import { 
  MessageSquare, 
  BookOpen, 
  FileText, 
  BarChart3, 
  Settings, 
  ChevronLeft,
  ChevronRight,
  User
} from "lucide-react";

type NavItem = {
  href: string;
  label: string;
  icon: any;
  adminOnly?: boolean;
};

const NAV: NavItem[] = [
  { href: "/chat",      label: "Chat",       icon: MessageSquare },
  { href: "/courses",   label: "Cours",      icon: BookOpen },
  { href: "/documents", label: "Documents",  icon: FileText, adminOnly: true },
  { href: "/analytics", label: "Analytics",  icon: BarChart3, adminOnly: true },
  { href: "/settings",  label: "Paramètres", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [role, setRole] = useState<"student" | "admin">("student");
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const token = tokenStore.getAccess();
    if (token) setRole(getUserRole(token) ?? "student");
  }, []);

  const visible = NAV.filter((n) => !n.adminOnly || role === "admin");

  return (
    <aside
      className={`flex flex-col h-screen bg-slate-50 border-r border-slate-200 shadow-sm transition-all duration-300 ${
        collapsed ? "w-20" : "w-64"
      }`}
    >
      {/* Logo Section */}
      <div className="flex items-center gap-3 px-6 py-6 border-b border-slate-200">
        {!collapsed && (
          <span className="text-2xl font-serif font-bold text-slate-900 tracking-tight">
            n7<span className="text-brand">chat</span>
          </span>
        )}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="ml-auto w-8 h-8 flex items-center justify-center rounded-lg bg-white border border-slate-200 text-slate-400 hover:text-brand hover:border-brand/40 transition-all shadow-sm"
          aria-label="Toggle sidebar"
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-6 space-y-2">
        {visible.map((item) => {
          const active = pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-4 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200 ${
                active
                  ? "bg-brand text-white shadow-lg shadow-brand/20 active:scale-95"
                  : "text-slate-600 hover:bg-white hover:text-brand hover:shadow-sm"
              }`}
            >
              <Icon size={20} className={`transition-transform duration-200 ${active ? "scale-110" : ""}`} />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* User Info / Role Badge */}
        <div className="px-6 pb-8 pt-4 border-t border-slate-200 flex justify-center">
          <div className="w-24 h-16 flex items-center justify-center opacity-80 hover:opacity-100 transition-opacity">
            <img 
              src="https://irvagmkpuxdeuckhawbv.supabase.co/storage/v1/object/public/logos/logo_enset.png" 
              alt="ENSET Logo"
              className="w-full h-full object-contain filter grayscale hover:grayscale-0 transition-all duration-500"
              onError={(e) => {
                (e.target as HTMLImageElement).src = "https://ui-avatars.com/api/?name=ENSET&background=transparent&color=slate";
              }}
            />
          </div>
        </div>
    </aside>
  );
}
