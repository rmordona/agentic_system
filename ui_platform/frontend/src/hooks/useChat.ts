// src/hooks/useChat.ts
import { useState, useCallback, useEffect } from "react";
import { useApi } from "@/hooks/useApi";

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  createdAt?: string;
}

interface SendThreadMessageRequest {
  content: string;
}

export const useChat = (threadId?: string) => {
  const api = useApi();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch messages for the current thread
   */
  const fetchMessages = useCallback(async () => {
    if (!threadId) return;

    setLoading(true);
    setError(null);

    try {
      // Match /routers/threads.py to avoid 307 redirect
      // If backend route is without trailing slash, then do not add trailing slash
      const endpoint = `/threads/${threadId}/messages`;
      const data = await api(endpoint);
      setMessages(data);
    } catch (err: any) {
      console.error("fetchMessages error:", err);
      setError(err.message || "Failed to fetch messages");
    } finally {
      setLoading(false);
    }
  }, [threadId, api]);

  /**
   * Send message to the thread
   */
  const sendMessage = useCallback(
    async (content: string) => {
      if (!threadId || !content.trim()) return;

      // Optimistic UI update
      const userMessage: ChatMessage = { role: "user", content };
      setMessages((prev) => [...prev, userMessage]);
      setLoading(true);
      setError(null);

      try {
        const body: SendThreadMessageRequest = { content };
        // Match /routers/threads.py to avoid 307 redirect
        // If backend route is without trailing slash, then do not add trailing slash
        console.log("see: ", content)
        const data = await api(`/chat/${threadId}`, {
          method: "POST",
          body: JSON.stringify({
            message: content,
            mode: "chat",
            artifacts: null,
            workspace: "stockticker_assistant"
          }),
        });

        // Add the response from backend as assistant message if returned
        if (data?.content) {
          const assistantMessage: ChatMessage = {
            role: "assistant",
            content: data.content,
          };
          setMessages((prev) => [...prev, assistantMessage]);
        }
      } catch (err: any) {
        console.error("sendMessage error:", err);
        setError(err.message || "Failed to send message");

        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "⚠️ Failed to get response from backend." },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [threadId, api]
  );


  return { messages, loading, error, fetchMessages, sendMessage };
};