// src/pages/ChatPage.tsx
import React, { useState } from "react";
import PlatformLayout from "../layouts/PlatformLayout";
import EngineeringPanel from "../components/sidebar/EngineeringPanel";
import ProductionPanel from "../components/sidebar/ProductionPanel";
import ChatWindow from "../components/chat/ChatWindow";
import MessageInput from "../components/chat/MessageInput";
import { useChat } from "../hooks/useChat";

const ChatPage = () => {
  // Mode: engineering or production
  const [mode, setMode] = useState<"engineering" | "production">("engineering");
  
  // Thread ID for multi-conversation support
  const [threadId, setThreadId] = useState<string>("default");

  // Hook to manage chat messages
  const { messages, sendMessage, loading } = useChat(threadId, mode);

  return (
    <PlatformLayout>
      <div className="flex flex-1 overflow-hidden h-full">
        {/* Left Panel */}
        <div className="w-1/4 bg-white border-r p-4 overflow-y-auto">
          {mode === "engineering" ? (
            <EngineeringPanel />
          ) : (
            <ProductionPanel messages={messages} />
          )}
        </div>

        {/* Main Chat Panel */}
        <div className="flex-1 flex flex-col p-6">
          <ChatWindow messages={messages} loading={loading} />
          <MessageInput
            onSend={async (msg) => {
              await sendMessage(msg);
            }}
            disabled={loading}
          />
        </div>
      </div>
    </PlatformLayout>
  );
};

export default ChatPage;