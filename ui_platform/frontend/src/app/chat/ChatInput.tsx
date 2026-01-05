import React, { useState } from "react";
import { useChatStore } from "./chatStore";

export default function ChatInput() {
  const [text, setText] = useState("");
  const addMessage = useChatStore((state) => state.addMessage);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;

    addMessage({ role: "user", content: text });
    setText("");

    // Call your LLM API here, streaming via SSE or async
    // e.g., call /api/agent/chat with text as payload
  };

  return (
    <form onSubmit={handleSubmit} className="mt-2 flex">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="flex-1 px-3 py-2 rounded-l-lg border focus:outline-none focus:ring-2 focus:ring-primary"
        placeholder="Type a message..."
      />
      <button type="submit" className="px-4 py-2 bg-primary text-white rounded-r-lg">
        Send
      </button>
    </form>
  );
}
