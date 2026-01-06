import React, { useState, useCallback } from 'react'
import ReactFlow, {
  addEdge,
  applyNodeChanges,
  Background,
  Controls,
  Edge,
  Node,
  Connection,
  ReactFlowProvider,
  MiniMap,
  OnLoadParams,
  NodeChange,
} from 'reactflow'
import 'reactflow/dist/style.css'
import NodeControlPanelView from './NodeControlPanelView' // <-- import

interface ReactFlowGraphViewProps {
  devMode?: boolean
}

// Initial nodes & edges
const initialNodes: Node[] = [
  {
    id: '1',
    type: 'default',
    data: { label: 'Node 1' },
    position: { x: 0, y: 0 },
    style: { background: '#1f2937', color: '#f9fafb', fontSize: 12, padding: 6, borderRadius: 6, width: 100 },
  },
  {
    id: '2',
    type: 'default',
    data: { label: 'Node 2' },
    position: { x: 200, y: 100 },
    style: { background: '#1f2937', color: '#f9fafb', fontSize: 12, padding: 6, borderRadius: 6, width: 100 },
  },
]

const initialEdges: Edge[] = [
  {
    id: 'e1-2',
    source: '1',
    target: '2',
    animated: true,
    style: { stroke: '#60a5fa', strokeWidth: 2 },
    data: { input: 'default', output: 'default' },
  },
]

export const ReactFlowGraphView: React.FC<ReactFlowGraphViewProps> = ({ devMode = false }) => {
  const [nodes, setNodes] = useState<Node[]>(initialNodes)
  const [edges, setEdges] = useState<Edge[]>(initialEdges)
  const [selectedElement, setSelectedElement] = useState<Node | Edge | null>(null)

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((nds) => applyNodeChanges(changes, nds))
  }, [])

  const onEdgesChange = useCallback(() => {}, [])

  const onConnect = useCallback(
    (connection: Connection) =>
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            animated: true,
            style: { stroke: '#60a5fa', strokeWidth: 2 },
            data: { input: 'default', output: 'default' },
          },
          eds
        )
      ),
    []
  )

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => setSelectedElement(node), [])
  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => setSelectedElement(edge), [])

  const onNodeMouseEnter = useCallback((_: React.MouseEvent, node: Node) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === node.id ? { ...n, style: { ...n.style, boxShadow: `0 0 0 3px #60a5fa` } } : n
      )
    )
  }, [])

  const onNodeMouseLeave = useCallback((_: React.MouseEvent, node: Node) => {
    setNodes((nds) =>
      nds.map((n) => (n.id === node.id ? { ...n, style: { ...n.style, boxShadow: undefined } } : n))
    )
  }, [])

  return (
    <ReactFlowProvider>
      <div className="w-full h-full bg-gray-900 rounded-lg border border-gray-700 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={devMode ? onConnect : undefined}
          nodesDraggable
          nodesConnectable={devMode}
          zoomOnScroll
          panOnDrag
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onNodeMouseEnter={onNodeMouseEnter}
          onNodeMouseLeave={onNodeMouseLeave}
          fitView
          style={{ fontSize: 12 }}
        >
          <Background gap={16} size={1} color="#374151" />
          <MiniMap
            nodeStrokeColor={(n) => (n.style?.background as string) || '#374151'}
            nodeColor={(n) => (n.style?.background as string) || '#1f2937'}
            nodeBorderRadius={6}
          />
          <Controls />
        </ReactFlow>
        <NodeControlPanelView
          selectedElement={selectedElement}
          nodes={nodes}
          edges={edges}
          setNodes={setNodes}
          setEdges={setEdges}
          setSelectedElement={setSelectedElement}
        />
      </div>
    </ReactFlowProvider>
  )
}

export default ReactFlowGraphView
