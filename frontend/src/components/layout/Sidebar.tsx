"use client";

import { useConversations } from "@/context/ConversationContext";
import { MessageSquare, BookOpen, Calendar, User, Plus, MessageCircle, MoreVertical, Trash2, FileUp } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import NextLink from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

export default function Sidebar() {
  const { user } = useAuth();
  const { conversations, activeConversation, setActiveConversation, createConversation, deleteConversation } = useConversations();
  const pathname = usePathname();
  const router = useRouter();

  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  const mainLinks = [
    { href: "/dashboard/chat", label: "Chat", icon: MessageSquare },
    { href: "/dashboard/courses", label: "Courses", icon: BookOpen },
    { href: "/dashboard/events", label: "Events", icon: Calendar },
    ...((user?.role === "admin") ? [{ href: "/dashboard/documents", label: "Documents", icon: FileUp }] : []),
    { href: "/dashboard/profile", label: "Profile", icon: User },
  ];

  const handleNewChat = async () => {
    await createConversation("New Conversation");
    router.push("/dashboard/chat");
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    await deleteConversation(id);
    setActiveMenuId(null);
  };

  return (
    <aside className="w-72 bg-sidebar-bg text-sidebar-text h-screen flex flex-col shrink-0 border-r border-slate-800 shadow-xl z-20">
      {/* Brand */}
      <div className="h-16 flex items-center px-6 shrink-0 bg-slate-900/50">
        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center mr-3 shadow-sm">
          <span className="text-white font-bold text-lg leading-none">N7</span>
        </div>
        <h1 className="text-xl font-bold tracking-tight text-white">N7Chat</h1>
      </div>

      {/* Primary Navigation */}
      <nav className="p-4 space-y-1 shrink-0 border-b border-slate-800">
        {mainLinks.map((link) => {
          const isActive = pathname.startsWith(link.href);
          const Icon = link.icon;
          return (
            <NextLink
              key={link.href}
              href={link.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-all duration-200 ${
                isActive 
                  ? "bg-primary text-white shadow-md shadow-primary/20" 
                  : "hover:bg-slate-800/50 hover:text-white"
              }`}
            >
              <Icon size={20} className={isActive ? "text-white" : "text-slate-400"} />
              {link.label}
            </NextLink>
          );
        })}
      </nav>

      {/* Conversations Section */}
      <div className="flex-1 overflow-y-auto flex flex-col p-4">
        <div className="flex items-center justify-between mb-4 px-1">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Conversations</h3>
          <button 
            onClick={handleNewChat}
            className="p-1 rounded bg-slate-800 text-slate-300 hover:bg-primary hover:text-white transition-colors"
            title="New Chat"
          >
            <Plus size={14} />
          </button>
        </div>

        <div className="flex-1 space-y-1">
          {conversations.length === 0 ? (
            <div className="text-center py-6 px-4">
              <MessageCircle size={32} className="mx-auto text-slate-600 mb-2 opacity-50" />
              <p className="text-sm text-slate-500">No conversations yet.</p>
            </div>
          ) : (
            conversations.map((conv) => {
              const isSelected = activeConversation?.id === conv.id && pathname === "/dashboard/chat";
              
              return (
                <div
                  key={conv.id}
                  onClick={() => {
                    setActiveConversation(conv);
                    if (pathname !== "/dashboard/chat") router.push("/dashboard/chat");
                  }}
                  className={`group relative flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                    isSelected ? "bg-slate-800 text-white" : "hover:bg-slate-800/50 text-slate-300"
                  }`}
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <MessageSquare size={16} className={isSelected ? "text-primary-light" : "text-slate-500"} />
                    <span className="text-sm truncate select-none">{conv.title}</span>
                  </div>
                  
                  {/* Action Menu Trigger */}
                  <button 
                    className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-slate-700 text-slate-400 hover:text-white transition-all focus:opacity-100"
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveMenuId(activeMenuId === conv.id ? null : conv.id);
                    }}
                  >
                    <MoreVertical size={14} />
                  </button>

                  {/* Dropdown Menu */}
                  {activeMenuId === conv.id && (
                    <div className="absolute right-2 top-10 w-32 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 overflow-hidden">
                      <button 
                        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-danger hover:bg-slate-700 transition"
                        onClick={(e) => handleDelete(e, conv.id)}
                      >
                        <Trash2 size={12} /> Delete
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </aside>
  );
}
