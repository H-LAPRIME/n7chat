/**
 * app/(dashboard)/chat/page.tsx
 * Main chat interface with streaming support.
 */
"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { tokenStore, getUserRole } from "@/lib/auth";
import { api } from "@/lib/api";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: string;
  sources?: { doc: string; page: number }[];
};

const QUICK_BUTTONS = {
  student: [
    "Explique-moi ce cours",
    "Quels sont les modules disponibles ?",
    "Résume le règlement intérieur",
    "Comment m'inscrire à un cours ?",
  ],
  admin: [
    "Ajouter un module",
    "Voir les statistiques",
    "Liste des étudiants inscrits",
    "Uploader un document PDF",
  ],
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [role, setRole] = useState<"student" | "admin">("student");
  const sessionId = useRef(crypto.randomUUID());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = tokenStore.getAccess();
    if (token) setRole(getUserRole(token) ?? "student");
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;
    const token = tokenStore.getAccess() ?? "";

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    // Placeholder assistant bubble
    const assistantId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: "assistant", content: "…" },
    ]);

    try {
      const res = await api.chat.send(text, sessionId.current, token);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: res.response,
                agent: res.agent_used,
                sources: res.sources,
              }
            : m
        )
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: "❌ Une erreur s'est produite. Réessayez." }
            : m
        )
      );
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  return (
    <div className="flex h-screen flex-col bg-[#0f0f1a] text-white">
      {/* Header */}
      <header className="flex items-center gap-3 border-b border-white/10 px-6 py-4">
        <span className="text-xl font-bold">
          n7<span className="text-[#6C5CE7]">chat</span>
        </span>
        <span className="ml-auto rounded-full bg-[#6C5CE7]/20 px-3 py-1 text-xs font-medium text-[#6C5CE7] capitalize">
          {role}
        </span>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-4 opacity-50">
            <span className="text-5xl">🧠</span>
            <p className="text-white/60">Posez votre première question…</p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-[#6C5CE7] text-white"
                  : "bg-white/8 border border-white/10 text-white/90"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.agent && (
                <p className="mt-1.5 text-xs opacity-50">via {msg.agent}</p>
              )}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 space-y-0.5">
                  {msg.sources.map((s, i) => (
                    <p key={i} className="text-xs text-[#00B894]/80">
                      📄 {s.doc} — p.{s.page}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Quick buttons */}
      <div className="flex gap-2 overflow-x-auto px-4 pb-2 scrollbar-hide">
        {QUICK_BUTTONS[role].map((q) => (
          <button
            key={q}
            onClick={() => sendMessage(q)}
            className="shrink-0 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/70 hover:border-[#6C5CE7]/60 hover:text-white transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="border-t border-white/10 px-4 py-4">
        <div className="flex items-end gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3">
          <textarea
            id="chat-input"
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Écrivez votre message… (Entrée pour envoyer)"
            className="flex-1 resize-none bg-transparent text-sm text-white placeholder-white/30 outline-none"
          />
          <button
            id="chat-send"
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            className="rounded-lg bg-[#6C5CE7] px-4 py-2 text-sm font-semibold text-white hover:bg-[#5a4bd1] disabled:opacity-40 transition-colors"
          >
            {loading ? "…" : "Envoyer"}
          </button>
        </div>
      </div>
    </div>
  );
}
