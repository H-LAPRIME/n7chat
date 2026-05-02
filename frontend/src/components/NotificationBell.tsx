/**
 * components/NotificationBell.tsx
 * A bell icon with a dropdown listing recent notifications.
 */
"use client";

import { useEffect, useState, useRef } from "react";
import { Bell, Check, Info, AlertTriangle, MessageSquare } from "lucide-react";
import { api } from "@/lib/api";
import { tokenStore } from "@/lib/auth";

type Notification = {
  id: string;
  title: string;
  message: string;
  type: "info" | "update" | "warning";
  is_read: boolean;
  timestamp: string;
};

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const unreadCount = notifications.filter(n => !n.is_read).length;

  useEffect(() => {
    const fetchNotifs = async () => {
      const token = tokenStore.getAccess();
      if (!token) return;
      try {
        const res = await api.notifications.list(token);
        setNotifications(res.notifications);
      } catch (e) {
        console.error("Failed to fetch notifications", e);
      }
    };

    fetchNotifs();
    const interval = setInterval(fetchNotifs, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function markRead(id: string) {
    const token = tokenStore.getAccess();
    if (!token) return;
    try {
      await api.notifications.markAsRead(id, token);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (e) {
      console.error(e);
    }
  }

  const getIcon = (type: string) => {
    switch (type) {
      case "update": return <Check size={14} className="text-green-500" />;
      case "warning": return <AlertTriangle size={14} className="text-brand" />;
      default: return <Info size={14} className="text-blue-500" />;
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2.5 rounded-xl text-slate-400 hover:text-brand hover:bg-slate-100 transition-all relative active:scale-95"
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span className="absolute top-2 right-2 w-2 h-2 bg-brand rounded-full border-2 border-white animate-pulse" />
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <h3 className="font-serif font-bold text-slate-900">Notifications</h3>
            <span className="text-[10px] font-bold text-brand bg-red-50 px-2 py-0.5 rounded-full uppercase tracking-widest">
              {unreadCount} Nouvelles
            </span>
          </div>

          <div className="max-h-[400px] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-10 text-center text-slate-400 italic text-sm">
                Aucune notification.
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => !n.is_read && markRead(n.id)}
                  className={`p-4 border-b border-slate-50 cursor-pointer transition-colors hover:bg-slate-50 group ${!n.is_read ? "bg-blue-50/20" : ""}`}
                >
                  <div className="flex gap-3">
                    <div className="mt-1">{getIcon(n.type)}</div>
                    <div className="flex-1">
                      <h4 className={`text-xs font-bold ${!n.is_read ? "text-slate-900" : "text-slate-500"}`}>
                        {n.title}
                      </h4>
                      <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">
                        {n.message}
                      </p>
                      <p className="text-[9px] text-slate-300 font-bold uppercase tracking-widest mt-2">
                        {new Date(n.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                    {!n.is_read && (
                      <div className="w-1.5 h-1.5 bg-brand rounded-full self-center" />
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="p-3 bg-slate-50 border-t border-slate-100 text-center">
            <button className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] hover:text-brand transition-colors">
              Voir tout l'historique
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
