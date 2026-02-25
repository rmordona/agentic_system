// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/prompts/PromptViewer.tsx
//
// Description:
//   Lightweight viewer for a single prompt and its corresponding output.
//   Ideal for embedding in side panels, modal popups, or focused views.
//
// Features:
//   - Displays prompt (input) and response (output) side-by-side or stacked
//   - Color-coded roles for clarity (user, system, agent)
//   - Scrollable content for long prompts/responses
//   - Can integrate with real-time updates
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

import React from 'react'

interface PromptViewerProps {
  role: 'user' | 'system' | 'agent'
  input: string
  output?: string
  className?: string
}

/**
 * PromptViewer component displays a single input/output pair with optional styling.
 *
 * @param role - Role of the sender (user, system, agent)
 * @param input - Prompt text sent to the agent
 * @param output - Response text from the agent (optional)
 * @param className - Optional additional styling
 */
const PromptViewer: React.FC<PromptViewerProps> = ({ role, input, output, className }) => {
  const roleColors: Record<string, string> = {
    user: 'bg-blue-100',
    system: 'bg-gray-100',
    agent: 'bg-green-100',
  }

  return (
    <div className={`prompt-viewer p-2 rounded shadow-sm ${className || ''}`}>
      <div className={`role-label px-2 py-0.5 rounded text-xs font-medium ${roleColors[role]}`}>
        {role.toUpperCase()}
      </div>
      <div className="mt-1 space-y-2">
        <div>
          <span className="font-semibold">Input:</span>
          <pre className="bg-gray-50 p-2 rounded overflow-x-auto">{input}</pre>
        </div>
        {output && (
          <div>
            <span className="font-semibold">Output:</span>
            <pre className="bg-gray-50 p-2 rounded overflow-x-auto">{output}</pre>
          </div>
        )}
      </div>
    </div>
  )
}

export default PromptViewer
