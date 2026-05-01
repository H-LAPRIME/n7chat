/**
 * lib/socket.ts
 * WebSocket client for real-time streaming chat via Flask-SocketIO.
 */

type MessageHandler = (data: { token: string }) => void;
type DoneHandler = (data: { session_id: string }) => void;

let socket: WebSocket | null = null;

export function connectSocket(token: string): WebSocket {
  const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:5000";

  if (socket && socket.readyState === WebSocket.OPEN) return socket;

  socket = new WebSocket(`${WS_URL}/chat?token=${token}`);

  socket.addEventListener("open", () => {
    console.log("[socket] connected");
  });

  socket.addEventListener("close", () => {
    console.log("[socket] disconnected");
    socket = null;
  });

  return socket;
}

export function sendSocketMessage(
  payload: { message: string; session_id: string },
  onToken: MessageHandler,
  onDone: DoneHandler
): void {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    console.error("[socket] not connected");
    return;
  }

  socket.send(JSON.stringify(payload));

  const handleMessage = (event: MessageEvent) => {
    const data = JSON.parse(event.data as string);
    if (data.type === "token") {
      onToken(data);
    } else if (data.type === "done") {
      onDone(data);
      socket?.removeEventListener("message", handleMessage);
    }
  };

  socket.addEventListener("message", handleMessage);
}

export function disconnectSocket(): void {
  socket?.close();
  socket = null;
}
