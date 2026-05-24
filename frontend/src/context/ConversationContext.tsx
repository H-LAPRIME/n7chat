"use client";

import React, { createContext, useCallback, useContext, useState, useEffect, ReactNode } from "react";
import { Conversation } from "@/lib/types";
import { fetchApi } from "@/lib/api";
import { useAuth } from "./AuthContext";

interface ConversationContextType {
  conversations: Conversation[];
  activeConversation: Conversation | null;
  setActiveConversation: (conv: Conversation | null) => void;
  loadConversations: () => Promise<void>;
  createConversation: (title: string) => Promise<Conversation>;
  deleteConversation: (id: string) => Promise<void>;
  renameConversation: (id: string, title: string) => Promise<void>;
}

const ConversationContext = createContext<ConversationContextType | undefined>(undefined);

export function ConversationProvider({ children }: { children: ReactNode }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const { user } = useAuth();

  const loadConversations = useCallback(async () => {
    if (!user) return;
    try {
      const data = await fetchApi<Conversation[]>("/chat/conversations");
      setConversations(data);
      // Optional: automatically select the most recent if none is selected
    } catch (e) {
      console.error("Failed to load conversations", e);
    }
  }, [user]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadConversations();
  }, [loadConversations]);

  const createConversation = async (title: string) => {
    const newConv = await fetchApi<Conversation>("/chat/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
    setConversations((prev) => [newConv, ...prev]);
    setActiveConversation(newConv);
    return newConv;
  };

  const deleteConversation = async (id: string) => {
    await fetchApi(`/chat/conversations/${id}`, { method: "DELETE" });
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConversation?.id === id) {
      setActiveConversation(null);
    }
  };

  const renameConversation = async (id: string, title: string) => {
    const updated = await fetchApi<Conversation>(`/chat/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    });
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title: updated.title } : c))
    );
    if (activeConversation?.id === id) {
      setActiveConversation({ ...activeConversation, title: updated.title });
    }
  };

  return (
    <ConversationContext.Provider
      value={{
        conversations,
        activeConversation,
        setActiveConversation,
        loadConversations,
        createConversation,
        deleteConversation,
        renameConversation,
      }}
    >
      {children}
    </ConversationContext.Provider>
  );
}

export function useConversations() {
  const context = useContext(ConversationContext);
  if (context === undefined) {
    throw new Error("useConversations must be used within a ConversationProvider");
  }
  return context;
}
