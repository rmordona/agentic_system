import React from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import "@/styles/productionpanel.css"; // centralized CSS

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  messages: Message[];
}

const ProductionPanel: React.FC<Props> = ({ messages }) => {
  return (
    <div className="production-panel">
      <h2>Conversation History</h2>
      <ScrollArea className="scroll-area">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={msg.role === "assistant" ? "message-assistant" : "message-user"}
          >
            <strong>{msg.role}:</strong> {msg.content}
          </div>
        ))}
      </ScrollArea>
    </div>
  );
};

export default ProductionPanel;