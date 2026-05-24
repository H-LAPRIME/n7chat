"use client";

import { ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { useConversations } from "@/context/ConversationContext";
import { fetchApi, getApiUrl } from "@/lib/api";
import { ChatArtifact, Message } from "@/lib/types";
import { getAccessToken } from "@/lib/auth";
import { streamChat } from "@/lib/sse";
import { Send, User as UserIcon, Bot, Info, Loader2, Download } from "lucide-react";

// ── Typing animation styles ────────────────────────────────────────────────
const TYPING_STYLES = `
  @keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0; }
  }
  @keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .streaming-cursor::after {
    content: '▋';
    display: inline-block;
    margin-left: 1px;
    animation: blink 0.7s step-end infinite;
    color: #6366f1;
    font-size: 0.9em;
    vertical-align: baseline;
  }
  .msg-enter {
    animation: fadeSlideIn 0.25s ease both;
  }
`;

function isTableSeparator(line: string) {
  return /^\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(line.trim());
}

function looksLikeMarkdown(content: string) {
  const lines = content.split("\n").map((line) => line.trim());
  return lines.some((line) => line.startsWith("#")) || lines.some((line, index) => line.startsWith("|") && isTableSeparator(lines[index + 1] || ""));
}

function renderInlineMarkdown(value: string) {
  return value.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function MarkdownMessage({ content }: { content: string }) {
  const lines = content.split("\n");
  const nodes: ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trim();

    if (!line) {
      index += 1;
      continue;
    }

    if (line.startsWith("### ")) {
      nodes.push(<h3 key={index} className="text-base font-bold mt-2 mb-2 text-text">{renderInlineMarkdown(line.slice(4))}</h3>);
      index += 1;
      continue;
    }

    if (line.startsWith("## ")) {
      nodes.push(<h2 key={index} className="text-lg font-bold mt-2 mb-2 text-text">{renderInlineMarkdown(line.slice(3))}</h2>);
      index += 1;
      continue;
    }

    if (line.startsWith("# ")) {
      nodes.push(<h1 key={index} className="text-xl font-bold mt-2 mb-2 text-text">{renderInlineMarkdown(line.slice(2))}</h1>);
      index += 1;
      continue;
    }

    if (line.startsWith("|") && lines[index + 1] && isTableSeparator(lines[index + 1])) {
      const headers = line.split("|").map((cell) => cell.trim()).filter(Boolean);
      const rows: string[][] = [];
      index += 2;

      while (index < lines.length && lines[index].trim().startsWith("|")) {
        rows.push(lines[index].split("|").map((cell) => cell.trim()).filter(Boolean));
        index += 1;
      }

      nodes.push(
        <div key={index} className="my-3 overflow-x-auto rounded-lg border border-border">
          <table className="w-full border-collapse text-sm">
            <thead className="bg-surface-2 text-text">
              <tr>
                {headers.map((header, cellIndex) => (
                  <th key={cellIndex} className="px-3 py-2 text-left font-bold border-b border-border">
                    {renderInlineMarkdown(header)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="odd:bg-white even:bg-surface-2/60">
                  {headers.map((_, cellIndex) => (
                    <td key={cellIndex} className="px-3 py-2 align-top border-b border-border/60">
                      {renderInlineMarkdown(row[cellIndex] || "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    nodes.push(<p key={index} className="my-1 leading-relaxed">{renderInlineMarkdown(line)}</p>);
    index += 1;
  }

  return <div className="space-y-1">{nodes}</div>;
}

async function downloadArtifact(artifact: ChatArtifact) {
  if (!artifact.download_url) return;
  const token = getAccessToken();
  if (!token) return;

  const response = await fetch(`${getApiUrl()}${artifact.download_url}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error("PDF download failed");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = artifact.file_name || `${artifact.type || "rapport"}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function ArtifactButton({ artifact }: { artifact: ChatArtifact }) {
  const [isDownloading, setIsDownloading] = useState(false);

  return (
    <button
      type="button"
      disabled={!artifact.download_url || isDownloading}
      onClick={async () => {
        setIsDownloading(true);
        try {
          await downloadArtifact(artifact);
        } finally {
          setIsDownloading(false);
        }
      }}
      className="mt-3 inline-flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700 hover:bg-emerald-100 disabled:opacity-60"
    >
      {isDownloading ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
      Télécharger le PDF
    </button>
  );
}

export default function ChatPage() {
  const { activeConversation, createConversation, loadConversations } = useConversations();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // ── Typewriter queue ──────────────────────────────────────────────────────
  // charQueue holds characters not yet rendered on screen.
  // The interval drains it at CHARS_PER_TICK chars every TICK_MS milliseconds.
  const TICK_MS = 16;        // ~60 fps
  const CHARS_PER_TICK = 3;  // chars revealed per tick  (~180 chars/s)
  const charQueue = useRef<string[]>([]);
  const typewriterRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamingIdRef = useRef<string | null>(null);
  const sseFinishedRef = useRef(false); // true once [DONE] received

  const startTypewriter = useCallback((assistantId: string) => {
    if (typewriterRef.current) return; // already running
    typewriterRef.current = setInterval(() => {
      if (charQueue.current.length === 0) {
        // Queue empty: stop only if SSE is also done
        if (sseFinishedRef.current) {
          clearInterval(typewriterRef.current!);
          typewriterRef.current = null;
          setIsStreaming(false);
          setStreamingId(null);
          streamingIdRef.current = null;
        }
        return;
      }
      const batch = charQueue.current.splice(0, CHARS_PER_TICK).join("");
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: m.content + batch } : m
        )
      );
    }, TICK_MS);
  }, []);

  const stopTypewriter = useCallback(() => {
    if (typewriterRef.current) {
      clearInterval(typewriterRef.current);
      typewriterRef.current = null;
    }
    charQueue.current = [];
  }, []);
  // ─────────────────────────────────────────────────────────────────────────

  // Auto-scroll logic
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  // Load history when active conversation changes
  useEffect(() => {
    async function loadHistory() {
      if (!activeConversation) {
        setMessages([]);
        return;
      }
      setIsLoadingHistory(true);
      try {
        const history = await fetchApi<Message[]>(`/chat/conversations/${activeConversation.id}/messages`);
        // History returns newest first for infinite scroll, we need oldest first for UI
        setMessages(history.reverse());
      } catch {
        console.error("Failed to fetch history");
      } finally {
        setIsLoadingHistory(false);
      }
    }
    loadHistory();
  }, [activeConversation]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    // Use current active conversation or create one if none selected
    let convId = activeConversation?.id;
    if (!convId) {
      const newConv = await createConversation(input.slice(0, 30) + "...");
      convId = newConv.id;
    }

    const token = getAccessToken();
    if (!token) return;

    // Optimistically add user message
    const tempId = Date.now().toString();
    const newUserMsg: Message = {
      id: tempId,
      sender_type: "user",
      content: input,
      message_type: "text",
      created_at: new Date().toISOString()
    };
    
    // Add empty assistant message to stream into
    const assistantId = (Date.now() + 1).toString();
    const newAssistantMsg: Message = {
        id: assistantId,
        sender_type: "assistant",
        content: "",
        message_type: "text",
        created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, newUserMsg, newAssistantMsg]);
    setInput("");
    setIsStreaming(true);
    setStreamingId(assistantId);
    streamingIdRef.current = assistantId;
    sseFinishedRef.current = false;
    charQueue.current = [];
    startTypewriter(assistantId);

    try {
      // Async generator loop — push chunks into the typewriter queue
      for await (const chunk of streamChat(convId, newUserMsg.content, token)) {
        if (chunk.chunk) {
          // Update message_type immediately (non-visible metadata)
          const text: string = chunk.chunk;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    message_type:
                      m.message_type === "markdown" || chunk.format === "markdown"
                        ? "markdown"
                        : "text",
                  }
                : m
            )
          );
          // Push characters into the queue for typewriter to drain
          charQueue.current.push(...text.split(""));
        } else if (chunk.error) {
          console.error("Stream error in event:", chunk.error);
          stopTypewriter();
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: chunk.error || "Streaming failed" } : m
            )
          );
        } else if (chunk.artifact) {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, artifact: chunk.artifact } : m))
          );
        }
      }
      await loadConversations();
    } catch (e) {
      console.error("Streaming failed", e);
      stopTypewriter();
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: "Streaming failed. Please try again." } : m
        )
      );
    } finally {
      // Signal typewriter that no more chunks are coming
      sseFinishedRef.current = true;
      // If queue is already empty, stop immediately
      if (charQueue.current.length === 0) {
        stopTypewriter();
        setIsStreaming(false);
        setStreamingId(null);
        streamingIdRef.current = null;
      }
    }
  };

  // Render empty state
  if (!activeConversation && messages.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center">
        <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mb-6">
          <Bot size={40} className="text-primary" />
        </div>
        <h2 className="text-3xl font-bold text-text mb-2">How can I help you?</h2>
        <p className="text-text-muted max-w-md mx-auto mb-8">
          Ask questions about your courses, university events, or let&apos;s just chat.
        </p>
        <div className="w-full max-w-2xl bg-white rounded-xl shadow-sm border border-border p-2">
            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Message N7Chat..."
                className="flex-1 px-4 py-3 bg-transparent outline-none"
              />
              <button 
                type="submit" 
                disabled={!input.trim()}
                className="btn-primary p-3 rounded-lg flex items-center justify-center aspect-square"
              >
                <Send size={20} />
              </button>
            </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-surface">
      {/* Inject typing animation keyframes */}
      <style>{TYPING_STYLES}</style>
      {/* Scrollable messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8 bg-surface-2/50 pt-10">
        {isLoadingHistory ? (
          <div className="flex justify-center items-center h-full">
            <Loader2 className="animate-spin text-primary" size={32} />
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((msg) => {
              const isUser = msg.sender_type === "user";
              const isCurrentlyStreaming = msg.id === streamingId;
              const isEmpty = !msg.content;

              return (
                <div key={msg.id} className={`flex gap-4 msg-enter ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                  {/* Avatar */}
                  <div className={`shrink-0 w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center mt-1 border ${
                    isUser ? "bg-primary-light text-primary border-primary/20" : "bg-white text-emerald-600 border-border shadow-sm"
                  }`}>
                    {isUser ? <UserIcon size={20} /> : <Bot size={20} />}
                  </div>

                  {/* Message Bubble */}
                  <div className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-5 py-3.5 shadow-sm ${
                    isUser
                      ? "bg-primary text-white rounded-tr-sm"
                      : "bg-white border border-border text-text rounded-tl-sm"
                  }`}>
                    <div className="font-medium leading-relaxed" style={{ wordBreak: "break-word" }}>
                      {/* Waiting dots — shown only before first chunk arrives */}
                      {isEmpty && isCurrentlyStreaming ? (
                        <span className="flex gap-1 items-center h-6">
                          <span className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" />
                          <span className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                          <span className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                        </span>
                      ) : msg.content ? (
                        /* Content: markdown or plain, with blinking cursor while streaming */
                        <span className={isCurrentlyStreaming ? "streaming-cursor" : ""}>
                          {!isUser && (msg.message_type === "markdown" || looksLikeMarkdown(msg.content))
                            ? <MarkdownMessage content={msg.content} />
                            : <span className="whitespace-pre-wrap">{msg.content}</span>
                          }
                        </span>
                      ) : null}
                      {!isUser && msg.artifact ? <ArtifactButton artifact={msg.artifact} /> : null}
                    </div>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} className="h-4" />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="p-4 bg-white border-t border-border shrink-0">
        <div className="max-w-4xl mx-auto relative">
          <form onSubmit={handleSubmit} className="flex items-end gap-2 bg-surface-2 p-2 rounded-2xl border border-border focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20 transition-all shadow-sm">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder="Message learning assistant..."
              className="flex-1 max-h-32 min-h-[44px] bg-transparent outline-none resize-none px-3 py-2.5 overflow-hidden"
              rows={1}
            />
            <button 
              type="submit" 
              disabled={!input.trim() || isStreaming}
              className={`p-3 rounded-xl flex items-center justify-center transition-all ${
                input.trim() && !isStreaming 
                  ? "bg-primary text-white hover:bg-primary-dark shadow-sm" 
                  : "bg-slate-200 text-slate-400 pointer-events-none"
              }`}
            >
              <Send size={20} />
            </button>
          </form>
          <div className="text-center mt-2">
            <p className="text-xs text-text-muted flex items-center justify-center gap-1">
              <Info size={12} /> N7Chat can make mistakes. Consider verifying important information.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
