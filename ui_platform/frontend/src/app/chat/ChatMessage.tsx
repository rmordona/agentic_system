import React from "react";

export default function ChatMessage({ message }: { message: any }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`px-4 py-2 rounded-lg ${isUser ? "bg-primary text-white" : "bg-gray-100 dark:bg-neutral text-black dark:text-white"}`}>
        {message.content}
      </div>
    </div>
  );
}
