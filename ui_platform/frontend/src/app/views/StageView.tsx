import React, { useEffect, useRef, useState, useCallback } from 'react'
import {
  ReactFlow,
  ReactFlowProvider,
  Node,
  Edge,
  ReactFlowInstance,
  NodeChange,
  EdgeChange,
  Connection,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  Background,
  Viewport,
} from 'reactflow'

import 'reactflow/dist/style.css'

import { WorkspaceContext } from '@/components/types/WorkspaceContext'


interface StageViewProps {
  nodes: Node[]
  edges: Edge[]
  isActive: boolean
  style?: React.CSSProperties
  nodeTypes?: any
  workspaceContext: WorkspaceContext
  viewport: Viewport
  onViewportChange: (vp: Viewport) => void
}

const StageView: React.FC<StageViewProps> = ({
  nodes,
  edges,
  isActive,
  style,
  nodeTypes,
  workspaceContext,
  viewport,
  onViewportChange,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const reactFlowRef = useRef<ReactFlowInstance | null>(null)

  const [localNodes, setLocalNodes] = useState<Node[]>(nodes)
  const [localEdges, setLocalEdges] = useState<Edge[]>(edges)
  const [selectedElement, setSelectedElement] = useState<Node | Edge | null>(null)

  // =======================
  // ReactFlow Callbacks
  // =======================
  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setLocalNodes(nds => applyNodeChanges(changes, nds))
  }, [])

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setLocalEdges(eds => applyEdgeChanges(changes, eds))
  }, [])

  const onConnect = useCallback((connection: Connection) => {
    setLocalEdges(eds =>
      addEdge(
        {
          ...connection,
          animated: true,
          type: 'bezier',
          markerEnd: { type: 'arrowclosed' },
          style: { stroke: '#60a5fa', strokeWidth: 2 },
        },
        eds
      )
    )
  }, [])

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedElement(node)
  }, [])

  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    setSelectedElement(edge)
  }, [])

  // =======================
  // Sync local state with props
  // =======================
  useEffect(() => {
    setLocalNodes(nodes)
  }, [nodes])

  useEffect(() => {
    setLocalEdges(edges)
  }, [edges])


  // listen to viewport change
  // reactflow v11+
  const handleMove = (event: any, viewport: Viewport) => {
   
  }


  // =======================
  // Render
  // =======================
  return (
    <div
      ref={containerRef}
      className="p-4 w-full h-[calc(100vh-4rem)] border rounded-lg"
      style={{
        display: isActive ? 'block' : 'none',
        width: '100%',
        height: '100%',
        position: 'absolute',
        top: 0,
        left: 0,
        ...style,
      }}
    >
      <ReactFlowProvider>
        <ReactFlow
          nodes={localNodes}
          edges={localEdges}
          nodeTypes={nodeTypes} /* This dictates the Nodes to be rendered */
          viewport={viewport}
          onMove={handleMove}
          // onViewportChange={onViewportChange}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          nodesDraggable
          nodesConnectable
          zoomOnScroll
          panOnDrag
          fitView={false}
          onInit={(instance) => (reactFlowRef.current = instance)}
          style={{ width: '100%', height: '100%' }}
        >
          <Background gap={16} size={1} color="#374151" />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  )
}

export default StageView
