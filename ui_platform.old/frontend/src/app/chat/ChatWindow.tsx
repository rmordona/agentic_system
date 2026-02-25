import React, { useEffect, useRef } from "react";
import { useChatStore } from "./chatStore";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";

export default function ChatWindow() {
  const messages = useChatStore((state) => state.messages);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new message
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-full p-4 bg-white dark:bg-background-dark rounded-lg shadow-panel">
      <div className="flex-1 overflow-y-auto space-y-2">
        {messages.map((msg, idx) => (
          <ChatMessage key={idx} message={msg} />
        ))}
        <div ref={scrollRef} />
      </div>
      <ChatInput />
    </div>
  );
}
