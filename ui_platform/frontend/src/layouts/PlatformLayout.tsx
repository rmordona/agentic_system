// src/layouts/PlatformLayout.tsx
import React, { useState, useEffect } from "react";
import "@/styles/platform.css";

import Topbar from "@/components/topbar/Topbar";
import RightPanel from "@/components/rightbar/RightPanel";
import EngineeringPanel from "@/components/sidebar/EngineeringPanel";
import ProductionPanel from "@/components/sidebar/ProductionPanel";
import ChatWindow from "@/components/chat/ChatWindow";
import MessageInput from "@/components/chat/MessageInput";
import ErrorDialog from "@/components/common/ErrorDialog";

import { useAuth } from "@/contexts/AuthContext";
import { useChat } from "@/hooks/useChat";
import { useApi } from "@/hooks/useApi";

// Represents a single conversation thread
interface Thread {
  id: string;
  name: string;
}

const PlatformLayout = () => {
  const [mode, setMode] = useState<"engineering" | "production">("engineering");
  const [activeTab, setActiveTab] = useState("home");

  const { accessToken, logout } = useAuth();
  const api = useApi(); // useApi automatically adds Authorization header

  const handleSignout = () => {
    logout();
  };

  // Threads state
  const [threads, setThreads] = useState<Thread[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [threadsError, setThreadsError] = useState<string | null>(null);

  // Chat hook for the selected thread
  const { messages, sendMessage, loading, fetchMessages, error: chatError } =
    useChat(threadId || undefined);

  // Load threads once accessToken is available
  useEffect(() => {
    if (!accessToken) return;

    const loadThreads = async () => {
      try {
        const data: Thread[] = await api("/threads/"); // no trailing slash
        setThreads(data);

        setThreadId((prev) => prev ?? (data.length ? data[0].id : null));
      } catch (err: any) {
        console.error("Failed to load threads:", err);
        setThreadsError(err.message || "Failed to load threads");
      }
    };

    loadThreads();
  }, [api, accessToken]); // ✅ api is stable now, no loop


  // Fetch messages whenever the selected thread changes
  useEffect(() => {
    if (!threadId) return;

    fetchMessages().catch((err) => {
      console.error("Error fetching messages for thread:", err);
    });
  }, [threadId]); // ✅ only run when threadId changes

  return (
    <>
      <div className="platform">
        {/* TOPBAR */}
        <div className="platform-topbar">
          <Topbar
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            mode={mode}
            setMode={setMode}
            onSignoutClick={handleSignout}
          />
        </div>

        {/* MAIN CONTENT */}
        <div className="platform-content">
          {/* LEFT THREAD SIDEBAR */}
          <div className="platform-thread-sidebar bg-gray-800 text-white p-2">
            <h3 className="font-semibold mb-2">Threads</h3>
            {threadsError && <div className="text-red-500 mb-2">{threadsError}</div>}
            <div className="flex flex-col gap-1">
              {threads.map((thread) => (
                <button
                  key={thread.id}
                  className={`text-left px-2 py-1 rounded ${
                    thread.id === threadId ? "bg-gray-700" : "hover:bg-gray-700"
                  }`}
                  onClick={() => setThreadId(thread.id)}
                >
                  {thread.name}
                </button>
              ))}
              {threads.length === 0 && !threadsError && (
                <div className="text-gray-400">No threads found</div>
              )}
            </div>
          </div>

          {/* SIDEBAR */}
          <div className="platform-sidebar">
            {mode === "engineering" ? (
              <EngineeringPanel />
            ) : (
              <ProductionPanel messages={messages} />
            )}
          </div>

          {/* MAIN CHAT */}
          <div className="platform-main">
            <div className="platform-chat-window">
              <ChatWindow messages={messages} loading={loading} />
            </div>
            <div className="platform-message-input">
              <MessageInput onSend={sendMessage} disabled={loading || !threadId} />
            </div>
          </div>

          {/* RIGHT BAR */}
          <div className="platform-rightbar">
            <RightPanel />
          </div>
        </div>

        {/* FOOTER */}
        <div className="platform-footer text-left text-sm">
          © 2026 Raymond M.O Ordona. All rights reserved.
        </div>
      </div>

      <ErrorDialog
        message={chatError}
        onClose={() => window.location.reload()}
      />
    </>
  );
};

export default PlatformLayout;