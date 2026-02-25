import { useEffect, useRef, useState, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";

export const useStreamingChat = (
  threadId: string,
  onChunk: (chunk: string) => void
) => {
  const { accessToken } = useAuth();

  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  /**
   * Establish WebSocket connection
   */
  useEffect(() => {
    if (!threadId || !accessToken) return;

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${protocol}://${window.location.host}/ws/chat/${threadId}?token=${accessToken}`;

    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;

    socket.onopen = () => {
      setConnected(true);
    };

    socket.onmessage = (event) => {
      onChunk(event.data);
    };

    socket.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    socket.onclose = () => {
      setConnected(false);
    };

    return () => {
      socket.close();
      wsRef.current = null;
      setConnected(false);
    };
  }, [threadId, accessToken, onChunk]);

  /**
   * Send message through WebSocket
   */
  const send = useCallback((message: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn("WebSocket is not connected.");
      return;
    }

    wsRef.current.send(JSON.stringify({ message }));
  }, []);

  return {
    send,
    connected,
  };
};