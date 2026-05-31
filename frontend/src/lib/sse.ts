import { clearTokens, getRefreshToken, saveTokens } from "./auth";
import { getApiUrl } from "./api";
import { ChatArtifact } from "./types";

type StreamChunk = {
  chunk?: string;
  format?: "text" | "markdown";
  artifact?: ChatArtifact;
  error?: string;
};

type TokenResponse = {
  access_token: string;
  refresh_token: string;
};

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  const response = await fetch(`${getApiUrl()}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    clearTokens();
    return null;
  }

  const data = (await response.json()) as TokenResponse;
  saveTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

async function openChatStream(
  conversationId: string,
  message: string,
  token: string,
  signal?: AbortSignal
) {
  return fetch(`${getApiUrl()}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      message,
    }),
    signal,
  });
}

export async function* streamChat(
  conversationId: string,
  message: string,
  token: string,
  signal?: AbortSignal
): AsyncGenerator<StreamChunk> {
  let response = await openChatStream(conversationId, message, token, signal);

  if (response.status === 401) {
    const refreshedToken = await refreshAccessToken();
    if (refreshedToken) {
      response = await openChatStream(conversationId, message, refreshedToken, signal);
    }
  }

  if (!response.ok) {
    throw new Error(`Stream failed: ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error("No response body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const dataStr = line.replace("data: ", "").trim();
        
        if (dataStr === "[DONE]") {
          return;
        }

        try {
          const parsed = JSON.parse(dataStr) as StreamChunk;
          yield parsed;
        } catch {
          console.error("Failed to parse SSE line", dataStr);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
