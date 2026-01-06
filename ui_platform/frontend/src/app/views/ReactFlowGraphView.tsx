import React, { useState, useCallback } from 'react'
import ReactFlow, {
  Background,
  Controls,
  addEdge,
  Node,
  Edge,
  Connection,
  ReactFlowInstance,
  MiniMap,
} from 'reactflow'
import 'reactflow/dist/style.css'

interface ReactFlowGraphViewProps {
  devMode?: boolean
}

const initialNodes: Node[] = [
  { id: '1', type: 'input', data: { label: 'Start Node' }, position: { x: 250, y: 5 } },
  { id: '2', data: { label: 'End Node' }, position: { x: 250, y: 150 } },
]

const initialEdges: Edge[] = [{ id: 'e1-2', source: '1', target: '2', animated: true }]

const ReactFlowGraphView: React.FC<ReactFlowGraphViewProps> = ({ devMode = false }) => {
  const [nodes, setNodes] = useState<Node[]>(initialNodes)
  const [edges, setEdges] = useState<Edge[]>(initialEdges)
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null)

  const onNodesChange = useCallback(
    (changes: any) => setNodes((nds) => nds.map((node) => ({ ...node, ...changes }))),
    []
  )

  const onEdgesChange = useCallback(
    (changes: any) => setEdges((eds) => eds.map((edge) => ({ ...edge, ...changes }))),
    []
  )

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    []
  )

  return (
    <div className="h-full w-full bg-gray-900">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
        onInit={setReactFlowInstance}
        style={{ backgroundColor: '#1f2937' }}
      >
        {/* Subtle dark grid */}
        <Background color="#4B5563" gap={20} size={1} />
        {/* Zoom & pan controls */}
        <Controls showZoom showFitView showInteractive />
        {/* MiniMap */}
        <MiniMap
          nodeStrokeColor={() => '#4B5563'}
          nodeColor={() => (devMode ? '#FBBF24' : '#374151')}
          nodeBorderRadius={2}
        />
      </ReactFlow>
    </div>
  )
}

export default ReactFlowGraphView

