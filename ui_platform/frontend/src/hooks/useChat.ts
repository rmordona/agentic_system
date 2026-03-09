// src/hooks/useChat.ts

import { useState, useCallback, useEffect, useRef } from "react";
import { useApi } from "@/hooks/useApi";
import { ChatSocket } from "@/services/chatSocket";

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  createdAt?: string;
}

interface HitlContext {
  agent: string;
  taskId: string;
  prompt: string;
}

export const useChat = (threadId?: string) => {
  const api = useApi();
  const socketRef = useRef<ChatSocket | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [hitlContext, setHitlContext] = useState<HitlContext | null>(null);
  const [awaitingResume, setAwaitingResume] = useState(false);

  const token = localStorage.getItem("access_token");

  // =====================================================
  // 🔌 WebSocket Lifecycle
  // =====================================================
const currentThreadRef = useRef<string | null>(null);

useEffect(() => {
  if (!threadId || !token) return;

  // If already connected for this thread, do nothing
  if (currentThreadRef.current === threadId && socketRef.current) {
    return;
  }

  // If switching threads, close old socket
  if (socketRef.current) {
    socketRef.current.close();
    socketRef.current = null;
  }

  const socket = new ChatSocket(threadId, token);

  socket.connect((data) => {
    // HITL
    if (data.type === "hitl_required" || data.type === "intent_clarification" || data.type === "intent_conversation") {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.prompt },
      ]);

      setHitlContext({
        agent: data.agent,
        taskId: data.task_id,
        prompt: data.prompt,
      });

      setAwaitingResume(true);
      setLoading(false);
      return;
    }

    // Token streaming
    if (data.type === "token") {
      const partial = data.content;
      if (!partial) return;

      setMessages((prev) => {
        const last = prev[prev.length - 1];

        if (last?.role === "assistant") {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...last,
            content: last.content + partial,
          };
          return updated;
        }

        return [...prev, { role: "assistant", content: partial }];
      });

      return;
    }

    // Completion
    if (data.type === "completion") {
      setLoading(false);
      setAwaitingResume(false);
      setHitlContext(null);
      return;
    }

    // Error
    if (data.type === "error") {
      setError(data.message || "Unknown error");
      setLoading(false);
      setAwaitingResume(false);
      return;
    }

    // ---------------------------------------
    // Internal Error
    // ---------------------------------------
    if (data.type === "internal_error") {
      setError(
        "An internal error occurred. Our team has been notified and is investigating."
      );
      setLoading(false);
      setAwaitingResume(false);
      return;
    }

    // ---------------------------------------
    // Connection Lost
    // ---------------------------------------
    if (data.type === "connection_lost") {
      setError(
        "Connection to the server was lost. Please refresh and try again."
      );
      setLoading(false);
      return;
    }


  });

  socketRef.current = socket;
  currentThreadRef.current = threadId;

  return () => {
    // Only close if component truly unmounts
    socket.close();
    socketRef.current = null;
    currentThreadRef.current = null;
  };
}, [threadId, token]);

  // =====================================================
  // Fetch History
  // =====================================================
  const fetchMessages = useCallback(async () => {
    if (!threadId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await api(`/threads/${threadId}/messages`);
      setMessages(data);
    } catch (err: any) {
      setError(err.message || "Failed to fetch messages");
    } finally {
      setLoading(false);
    }
  }, [threadId, api]);

  // =====================================================
  // Send Message
  // =====================================================
  const sendMessage = useCallback(
    (content: string) => {
      if (!threadId || !content.trim() || !socketRef.current) return;

      // Prevent duplicate resume clicks
      if (awaitingResume === false && loading) return;

      setError(null);

      // ==========================================
      // HITL Resume Mode
      // ==========================================
      if (hitlContext && awaitingResume) {
        socketRef.current.send({
          type: "hitl_response",
          content,
          workspace: "stockticker_assistant"
        });

        setMessages((prev) => [
          ...prev,
          { role: "user", content },
        ]);

        setAwaitingResume(false);
        setLoading(true);

        return;
      }

      // ==========================================
      // Normal User Message
      // ==========================================
      const userMessage: ChatMessage = { role: "user", content };
      setMessages((prev) => [...prev, userMessage]);

      setLoading(true);

      socketRef.current.send({
        type: "user_message",
        message: content,
        workspace: "stockticker_assistant",
      });
    },
    [threadId, hitlContext, awaitingResume, loading]
  );

  // =====================================================
  // Approval Helpers (Optional UI Helpers)
  // =====================================================
  const approve = () => {
    if (!hitlContext) return;
    sendMessage("approve");
  };

  const reject = () => {
    if (!hitlContext) return;
    sendMessage("reject");
  };

  return {
    messages,
    loading,
    error,

    hitlContext,
    awaitingResume,

    isWaitingForHuman: !!hitlContext && awaitingResume,
    isStreaming: loading && !awaitingResume,

    fetchMessages,
    sendMessage,
    approve,
    reject,
  };

};