// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/graph/EdgeInspector.tsx
//
// Description:
//   Inspector panel for viewing and editing properties of a selected edge in a React Flow graph.
//
//   Responsibilities:
//     - Display source and target node IDs
//     - Edit edge label or metadata
//     - Emit updates back to GraphEditor
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

import React, { useState, useEffect } from 'react'
import { Edge } from 'reactflow'

interface EdgeInspectorProps {
  edge: Edge | null
  onUpdate: (updatedEdge: Partial<Edge>) => void
}

/**
 * EdgeInspector component allows the user to inspect and edit a selected edge.
 */
const EdgeInspector: React.FC<EdgeInspectorProps> = ({ edge, onUpdate }) => {
  const [label, setLabel] = useState('')

  useEffect(() => {
    if (edge) {
      setLabel(edge.label as string || '')
    }
  }, [edge])

  /**
   * Handle label input change and propagate to parent
   */
  const handleLabelChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newLabel = e.target.value
    setLabel(newLabel)
    if (edge) {
      onUpdate({ id: edge.id, label: newLabel })
    }
  }

  if (!edge) return <div className="inspector-empty">Select an edge to inspect</div>

  return (
    <div className="edge-inspector">
      <h3>Edge Inspector</h3>
      <p>
        <strong>Source:</strong> {edge.source} <br />
        <strong>Target:</strong> {edge.target}
      </p>
      <label>
        Label:
        <input type="text" value={label} onChange={handleLabelChange} />
      </label>
    </div>
  )
}

export default EdgeInspector
