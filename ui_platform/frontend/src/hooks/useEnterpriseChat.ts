import { useState } from "react";
import { useApi } from "@/hooks/useApi";

export interface Message {
  role: "user" | "assistant";
  content: string;
}

interface EnterpriseChatRequest {
  message: string;
  mode: "engineering" | "production";
  artifacts?: any;
}

export const useEnterpriseChat = (
  threadId: string,
  mode: "engineering" | "production"
) => {
  const api = useApi();

  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async (content: string, artifacts?: any) => {
    if (!threadId || !content.trim()) return;

    // Optimistic user message
    const userMessage: Message = {
      role: "user",
      content,
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const body: EnterpriseChatRequest = {
        message: content,
        mode,
        artifacts,
      };

      const data = await api(`/chat/${threadId}`, {
        method: "POST",
        body: JSON.stringify(body),
      });

      const assistantMessage: Message = {
        role: "assistant",
        content:
          typeof data.content === "string"
            ? data.content
            : JSON.stringify(data.content, null, 2),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Enterprise chat error:", err);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "⚠️ Enterprise agent failed to respond.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return {
    messages,
    sendMessage,
    loading,
  };
};