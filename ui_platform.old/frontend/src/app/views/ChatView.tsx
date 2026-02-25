// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: src/app/views/ChatView.tsx
//
// Description:
//   Contextual chat component for RunView and GraphEditorView.
//   Supports two modes: 'user' and 'developer'.
//   - User mode: query-only, read-only view of run/graph data
//   - Developer mode: can input commands and see stage-to-stage flow
//
// Features:
//   - Mode badge
//   - Scrollable chat history
//   - Input box with submit
//   - Dev-only simulation / stage preview
// -----------------------------------------------------------------------------

import React, { useState, useEffect, useRef } from 'react'

interface ChatMessage {
  id: number
  role: 'system' | 'user' | 'developer'
  content: string
}

interface ChatViewProps {
  workspaceId: string
  runId?: string
  mode: 'user' | 'developer'
}

const ChatView: React.FC<ChatViewProps> = ({ workspaceId, runId, mode }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Safe conversion
  const displayMode = (mode || 'user').toUpperCase()

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Handle submitting a message
  const handleSubmit = () => {
    if (!inputValue.trim()) return

    const newMessage: ChatMessage = {
      id: messages.length + 1,
      role: mode === 'developer' ? 'developer' : 'user',
      content: inputValue,
    }

    setMessages((prev) => [...prev, newMessage])
    setInputValue('')

    // Simulate system / stage flow response
    setTimeout(() => {
      const systemMessage: ChatMessage = {
        id: messages.length + 2,
        role: 'system',
        content:
          mode === 'developer'
            ? `Simulated stage flow for "${newMessage.content}" in workspace ${workspaceId}${runId ? `, run ${runId}` : ''}.`
            : `Response to "${newMessage.content}" in workspace ${workspaceId}${runId ? `, run ${runId}` : ''}.`,
      }
      setMessages((prev) => [...prev, systemMessage])
    }, 500)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex flex-col h-full border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
      {/* Header with mode badge */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-100 dark:bg-gray-800 border-b dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">
          Chat {runId ? `(Run ${runId})` : ''}
        </h3>
        <span
          className={`px-2 py-1 text-xs font-medium rounded ${
            mode === 'developer' ? 'bg-orange-500 text-white' : 'bg-blue-500 text-white'
          }`}
        >
          {displayMode}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-4 space-y-2">
        {messages.map((msg) => (
          <div key={msg.id} className={`p-2 rounded-md ${msg.role === 'system' ? 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-100' : msg.role === 'developer' ? 'bg-orange-200 dark:bg-orange-700 text-orange-900 dark:text-orange-100' : 'bg-blue-200 dark:bg-blue-700 text-blue-900 dark:text-blue-100'}`}>
            <strong>{(msg.role || 'role').toUpperCase()}:</strong> {msg.content}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input field */}
      <div className="flex p-2 border-t dark:border-gray-700 bg-gray-100 dark:bg-gray-800">
        <input
          type="text"
          className="flex-1 px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-50 focus:outline-none focus:ring focus:border-blue-400 dark:focus:border-blue-500"
          placeholder={mode === 'developer' ? 'Enter dev command...' : 'Enter your question...'}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          onClick={handleSubmit}
          className="ml-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
        >
          Send
        </button>
      </div>
    </div>
  )
}

export default ChatView

