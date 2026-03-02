import React from "react";
import { useParams } from "react-router-dom";
import ChatWindow from "@/chat/ChatWindow";
import MessageInput from "@/chat/MessageInput";
import { useChat } from "@/hooks/useChat";

const ChatPage: React.FC = () => {
  const { threadId } = useParams<{ threadId: string }>();

  const {
    messages,
    loading,
    sendMessage,
    approve,
    reject,
    isWaitingForHuman,
    isStreaming,
  } = useChat(threadId);

  return (
    <div className="chat-page">
      <ChatWindow
        messages={messages}
        loading={isStreaming}
        isWaitingForHuman={isWaitingForHuman}
      />

      <MessageInput
        onSend={sendMessage}
        onApprove={approve}
        onReject={reject}
        disabled={loading}
        isWaitingForHuman={isWaitingForHuman}
      />
    </div>
  );
};

export default ChatPage;