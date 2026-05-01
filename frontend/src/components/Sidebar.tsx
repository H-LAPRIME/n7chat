/**
 * components/Sidebar.tsx
 * Collapsible role-aware navigation sidebar.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { tokenStore, getUserRole } from "@/lib/auth";

type NavItem = {
  href: string;
  label: string;
  icon: string;
  adminOnly?: boolean;
};

const NAV: NavItem[] = [
  { href: "/chat",      label: "Chat",       icon: "💬" },
  { href: "/courses",   label: "Cours",      icon: "📚" },
  { href: "/documents", label: "Documents",  icon: "📄", adminOnly: true },
  { href: "/analytics", label: "Analytics",  icon: "📊", adminOnly: true },
  { href: "/settings",  label: "Paramètres", icon: "⚙️" },
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
      className={`flex flex-col h-screen bg-[#0d0d1b] border-r border-white/8 transition-all duration-300 ${
        collapsed ? "w-16" : "w-56"
      }`}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-5 border-b border-white/8">
        {!collapsed && (
          <span className="text-lg font-bold text-white">
            n7<span className="text-[#6C5CE7]">chat</span>
          </span>
        )}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="ml-auto text-white/40 hover:text-white transition-colors text-sm"
          aria-label="Toggle sidebar"
        >
          {collapsed ? "→" : "←"}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {visible.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                active
                  ? "bg-[#6C5CE7]/20 text-[#6C5CE7] font-medium"
                  : "text-white/50 hover:bg-white/5 hover:text-white"
              }`}
            >
              <span className="text-base">{item.icon}</span>
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Role badge */}
      {!collapsed && (
        <div className="px-4 py-4 border-t border-white/8">
          <span className="rounded-full bg-[#6C5CE7]/15 px-3 py-1 text-xs font-medium text-[#6C5CE7] capitalize">
            {role}
          </span>
        </div>
      )}
    </aside>
  );
}
