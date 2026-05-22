"use client";

import { useEffect, useRef, useState } from "react";
import { useConversations } from "@/context/ConversationContext";
import { useAuth } from "@/context/AuthContext";
import { fetchApi } from "@/lib/api";
import { Message } from "@/lib/types";
import { getAccessToken } from "@/lib/auth";
import { streamChat } from "@/lib/sse";
import { Send, User as UserIcon, Bot, Info, Loader2 } from "lucide-react";

export default function ChatPage() {
  const { activeConversation, createConversation } = useConversations();
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
        const history = await fetchApi(`/chat/conversations/${activeConversation.id}/messages`);
        // History returns newest first for infinite scroll, we need oldest first for UI
        setMessages(history.reverse());
      } catch (e) {
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

    try {
      // Async generator loop
      for await (const chunk of streamChat(convId, newUserMsg.content, token)) {
        if (chunk.chunk) {
          setMessages((prev) => 
            prev.map(m => m.id === assistantId ? { ...m, content: m.content + chunk.chunk } : m)
          );
        } else if (chunk.error) {
          console.error("Stream error in event:", chunk.error);
        }
      }
    } catch (e) {
      console.error("Streaming failed", e);
    } finally {
      setIsStreaming(false);
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
          Ask questions about your courses, university events, or let's just chat.
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
              
              return (
                <div key={msg.id} className={`flex gap-4 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
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
                    <div className="whitespace-pre-wrap flex flex-col gap-2 font-medium leading-relaxed" style={{ wordBreak: 'break-word' }}>
                      {msg.content || (msg.sender_type === "assistant" && isStreaming && msg.id === messages[messages.length-1].id ? <span className="flex gap-1 items-center h-6"><span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"></span><span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span><span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span></span> : null)}
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
