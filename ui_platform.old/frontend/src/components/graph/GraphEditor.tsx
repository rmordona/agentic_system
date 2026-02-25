// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/graph/GraphEditor.tsx
//
// Description:
//   Full-featured graph editor using React Flow.
//
//   Responsibilities:
//     - Render nodes and edges
//     - Handle selection and editing via NodeInspector and EdgeInspector
//     - Support dynamic updates and observability
//     - Provide developer/user mode switch
//     - Integrate with workspace graph state
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

import React, { useState, useCallback } from 'react'
import ReactFlow, {
  addEdge,
  Background,
  Connection,
  Edge,
  Node,
  OnNodesChange,
  OnEdgesChange,
  Controls,
  MiniMap,
  applyNodeChanges,
  applyEdgeChanges,
  useReactFlow,
} from 'reactflow'

import NodeInspector from './NodeInspector'
import EdgeInspector from './EdgeInspector'
import 'reactflow/dist/style.css'

interface GraphEditorProps {
  initialNodes: Node[]
  initialEdges: Edge[]
  developerMode?: boolean
}

/**
 * GraphEditor component allows users to visually edit nodes and edges in a workspace graph.
 */
const GraphEditor: React.FC<GraphEditorProps> = ({ initialNodes, initialEdges, developerMode = false }) => {
  const [nodes, setNodes] = useState<Node[]>(initialNodes)
  const [edges, setEdges] = useState<Edge[]>(initialEdges)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<Edge | null>(null)

  const reactFlowInstance = useReactFlow()

  /**
   * Handle node selection
   */
  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node)
    setSelectedEdge(null)
  }, [])

  /**
   * Handle edge selection
   */
  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    setSelectedEdge(edge)
    setSelectedNode(null)
  }, [])

  /**
   * Handle adding a new connection between nodes
   */
  const onConnect = useCallback((params: Edge | Connection) => {
    if (!developerMode) return
    setEdges((eds) => addEdge(params, eds))
  }, [developerMode])

  /**
   * Update node changes from NodeInspector
   */
  const handleNodeUpdate = (updatedNode: Partial<Node>) => {
    setNodes((nds) => nds.map((n) => (n.id === updatedNode.id ? { ...n, ...updatedNode } : n)))
  }

  /**
   * Update edge changes from EdgeInspector
   */
  const handleEdgeUpdate = (updatedEdge: Partial<Edge>) => {
    setEdges((eds) => eds.map((e) => (e.id === updatedEdge.id ? { ...e, ...updatedEdge } : e)))
  }

  return (
    <div className="graph-editor" style={{ display: 'flex', height: '100%' }}>
      <div style={{ flex: 1 }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={(changes) => setNodes((nds) => applyNodeChanges(changes, nds))}
          onEdgesChange={(changes) => setEdges((eds) => applyEdgeChanges(changes, eds))}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onConnect={onConnect}
          fitView
        >
          <MiniMap />
          <Controls />
          <Background />
        </ReactFlow>
      </div>

      {/* Inspector Panel */}
      <aside style={{ width: 300, padding: 10, borderLeft: '1px solid #ddd', overflowY: 'auto' }}>
        <NodeInspector node={selectedNode} onUpdate={handleNodeUpdate} />
        <EdgeInspector edge={selectedEdge} onUpdate={handleEdgeUpdate} />
      </aside>
    </div>
  )
}

export default GraphEditor
