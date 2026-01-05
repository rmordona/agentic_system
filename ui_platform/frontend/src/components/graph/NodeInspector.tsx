// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/graph/NodeInspector.tsx
//
// Description:
//   Inspector panel for viewing and editing properties of a selected node in a React Flow graph.
//
//   Responsibilities:
//     - Display node type and ID
//     - Edit node label or metadata
//     - Trigger updates back to GraphEditor
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

import React, { useState, useEffect } from 'react'
import { Node } from 'reactflow'

interface NodeInspectorProps {
  node: Node | null
  onUpdate: (updatedNode: Partial<Node>) => void
}

/**
 * NodeInspector component allows the user to inspect and edit a selected node.
 */
const NodeInspector: React.FC<NodeInspectorProps> = ({ node, onUpdate }) => {
  const [label, setLabel] = useState('')

  useEffect(() => {
    if (node) {
      setLabel(node.data?.label || '')
    }
  }, [node])

  /**
   * Handle label input change and propagate to parent
   */
  const handleLabelChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newLabel = e.target.value
    setLabel(newLabel)
    if (node) {
      onUpdate({ id: node.id, data: { ...node.data, label: newLabel } })
    }
  }

  if (!node) return <div className="inspector-empty">Select a node to inspect</div>

  return (
    <div className="node-inspector">
      <h3>Node Inspector</h3>
      <p>
        <strong>Node ID:</strong> {node.id} <br />
        <strong>Type:</strong> {node.type}
      </p>
      <label>
        Label:
        <input type="text" value={label} onChange={handleLabelChange} />
      </label>
    </div>
  )
}

export default NodeInspector
