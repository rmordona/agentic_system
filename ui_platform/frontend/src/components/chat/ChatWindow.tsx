import React from "react";
import { motion } from "framer-motion";
import "@/styles/chatwindow.css"; // centralized CSS

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  messages: Message[];
  loading?: boolean;
}

const ChatWindow: React.FC<Props> = ({ messages, loading = false }) => {
  return (
    <div className="chat-window">
      {messages.map((msg, idx) => (
        <motion.div
          key={idx}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={msg.role === "assistant" ? "chat-message-assistant" : "chat-message-user"}
        >
          <strong>{msg.role}:</strong> {msg.content}
        </motion.div>
      ))}
      {loading && <div className="chat-typing">Assistant is typing...</div>}
    </div>
  );
};

export default ChatWindow;