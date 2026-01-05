// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/prompts/IOInspector.tsx
//
// Description:
//   Inspector panel to visualize inputs and outputs of a workflow or agent stage.
//   Displays prompts sent to the LLM and the corresponding outputs or completions.
//
// Features:
//   - Shows multiple input/output pairs
//   - Supports expandable/collapsible panels per interaction
//   - Syntax highlighting for structured content
//   - Scrollable for long text
//   - Can integrate with SSE or state management for live updates
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

import React, { useState } from 'react'

interface IOEntry {
  id: string
  role: 'user' | 'system' | 'agent'
  input: string
  output?: string
}

interface IOInspectorProps {
  entries: IOEntry[]
}

/**
 * IOInspector component displays a chronological list of prompt/response entries
 * for a given workflow, stage, or agent interaction.
 *
 * @param entries - Array of input/output entries to display
 */
const IOInspector: React.FC<IOInspectorProps> = ({ entries }) => {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const copy = new Set(prev)
      if (copy.has(id)) copy.delete(id)
      else copy.add(id)
      return copy
    })
  }

  return (
    <div className="io-inspector max-h-full overflow-y-auto p-2">
      {entries.map((entry) => {
        const isExpanded = expandedIds.has(entry.id)
        return (
          <div
            key={entry.id}
            className="io-entry border rounded mb-2 p-2 bg-white shadow-sm"
          >
            <div
              className="io-header flex justify-between cursor-pointer"
              onClick={() => toggleExpand(entry.id)}
            >
              <span className="font-medium">{entry.role.toUpperCase()}</span>
              <span className="text-sm text-gray-500">
                {isExpanded ? '▼' : '▶'}
              </span>
            </div>
            {isExpanded && (
              <div className="io-content mt-1 space-y-2">
                <div>
                  <span className="font-semibold">Input:</span>
                  <pre className="bg-gray-50 p-2 rounded text-sm overflow-x-auto">
                    {entry.input}
                  </pre>
                </div>
                {entry.output && (
                  <div>
                    <span className="font-semibold">Output:</span>
                    <pre className="bg-gray-50 p-2 rounded text-sm overflow-x-auto">
                      {entry.output}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default IOInspector
