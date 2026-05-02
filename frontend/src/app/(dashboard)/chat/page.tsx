/**
 * app/(dashboard)/chat/page.tsx
 * Main chat interface with light academic theme.
 */
"use client";

import { useState, useRef, useEffect, KeyboardEvent, FormEvent } from "react";
import { tokenStore, getUserRole } from "@/lib/auth";
import { api } from "@/lib/api";
import { 
  Send, 
  GraduationCap, 
  BookOpen, 
  ListChecks, 
  Scale, 
  PenTool, 
  PlusCircle, 
  BarChart3, 
  Users, 
  Upload,
  FileText
} from "lucide-react";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: string;
  sources?: { doc: string; page: number }[];
};

const QUICK_BUTTONS = {
  student: [
    { id: 1, text: "Explique-moi ce cours", icon: BookOpen },
    { id: 2, text: "Quels sont les modules disponibles ?", icon: ListChecks },
    { id: 3, text: "Résume le règlement intérieur", icon: Scale },
    { id: 4, text: "Comment m'inscrire à un cours ?", icon: PenTool },
  ],
  admin: [
    { id: 1, text: "Ajouter un module", icon: PlusCircle },
    { id: 2, text: "Voir les statistiques", icon: BarChart3 },
    { id: 3, text: "Liste des étudiants inscrits", icon: Users },
    { id: 4, text: "Uploader un document PDF", icon: Upload },
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
            ? { ...m, content: "Une erreur s'est produite. Réessayez." }
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

  function handleSend(e: FormEvent) {
    e.preventDefault();
    sendMessage(input);
  }

  return (
    <div className="flex h-full bg-white text-slate-900">
      <div className="flex flex-1 flex-col relative">
        <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-32 scrollbar-thin scrollbar-thumb-slate-200">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center opacity-80">
              <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4 text-brand">
                <GraduationCap size={40} />
              </div>
              <h2 className="text-2xl font-serif font-bold text-slate-800">Bienvenue sur n7chat</h2>
              <p className="max-w-md text-slate-500 mt-2">
                Posez vos questions sur les cours, les documents ou la vie étudiante. 
                Je suis là pour vous accompagner dans votre réussite académique.
              </p>
              
              <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl px-4">
                {QUICK_BUTTONS[role].map((btn) => {
                  const Icon = btn.icon;
                  return (
                    <button
                      key={btn.id}
                      onClick={() => setInput(btn.text)}
                      className="flex items-center gap-3 p-4 rounded-xl border border-slate-200 bg-slate-50 hover:border-brand hover:bg-white hover:shadow-md transition text-left group"
                    >
                      <span className="p-2 rounded-lg bg-white border border-slate-100 text-slate-400 group-hover:text-brand transition-colors">
                        <Icon size={20} />
                      </span>
                      <span className="text-sm font-medium text-slate-700">{btn.text}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <>
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 shadow-sm ${
                      m.role === "user"
                        ? "bg-brand text-white shadow-brand/10"
                        : "bg-slate-100 text-slate-900 border border-slate-200"
                    }`}
                  >
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{m.content}</p>
                    {m.agent && (
                      <p className="mt-1.5 text-[10px] opacity-40 font-bold uppercase tracking-wider">
                        Assistant: {m.agent}
                      </p>
                    )}
                    {m.sources && m.sources.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-slate-200 space-y-1">
                        {m.sources.map((s, i) => (
                          <p key={i} className="text-[10px] text-brand/70 font-medium flex items-center gap-1">
                            <FileText size={10} /> {s.doc} — p.{s.page}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </>
          )}
        </div>

        {/* Input area */}
        <div className="absolute bottom-4 left-0 right-0 px-6 bg-transparent">
          <div className="absolute -bottom-4 left-0 right-0 h-24 bg-gradient-to-t from-white via-white/90 to-transparent -z-10 pointer-events-none" />
          <form
            onSubmit={handleSend}
            className="mx-auto max-w-4xl flex items-end gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl ring-1 ring-slate-200/50 focus-within:ring-brand/20 focus-within:border-brand/30 transition-all"
          >
            <textarea
              className="flex-1 bg-transparent px-4 py-2.5 text-sm text-slate-900 !outline-none !ring-0 !border-none placeholder-slate-400 max-h-32 resize-none shadow-none"
              placeholder="Posez votre question... (Entrée pour envoyer)"
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-xl bg-brand p-2.5 text-white shadow-sm hover:bg-brand-hover disabled:opacity-40 transition-all active:scale-95"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <Send size={20} />
              )}
            </button>
          </form>
          <p className="mt-3 text-center text-[10px] text-slate-400 uppercase tracking-widest font-bold flex items-center justify-center gap-2">
            <GraduationCap size={12} /> Propulsé par l&apos;IA de n7chat — Excellence Académique
          </p>
        </div>
      </div>
    </div>
  );
}
