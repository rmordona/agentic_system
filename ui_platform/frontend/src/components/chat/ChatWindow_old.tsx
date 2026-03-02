import React, { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import "@/styles/chatwindow.css";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  messages: Message[];
  loading?: boolean;
  isWaitingForHuman?: boolean;
}

const ChatWindow: React.FC<Props> = ({
  messages,
  loading = false,
  isWaitingForHuman = false,
}) => {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // 🔽 Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="chat-window">
      {messages.map((msg, idx) => {
        const isLast = idx === messages.length - 1;

        return (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={
              msg.role === "assistant"
                ? "chat-message-assistant"
                : "chat-message-user"
            }
          >
            <strong>{msg.role}:</strong>{" "}
            {msg.content}
            {/* ✨ Streaming cursor */}
            {loading && isLast && msg.role === "assistant" && (
              <span className="chat-cursor">▍</span>
            )}
          </motion.div>
        );
      })}

      {loading && !isWaitingForHuman && (
        <div className="chat-typing">Assistant is typing...</div>
      )}

      {isWaitingForHuman && (
        <div className="chat-hitl-banner">
          Awaiting your approval...
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};

export default ChatWindow;