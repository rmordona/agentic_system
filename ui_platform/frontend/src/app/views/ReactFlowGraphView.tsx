import React, { useState, useCallback } from 'react'
import ReactFlow, {
  addEdge,
  Background,
  Controls,
  Edge,
  Node,
  Connection,
  ReactFlowProvider,
  MiniMap,
  OnLoadParams,
  NodeProps,
  EdgeProps,
} from 'reactflow'
import 'reactflow/dist/style.css'

interface ReactFlowGraphViewProps {
  devMode?: boolean
}

const initialNodes: Node[] = [
  { id: '1', type: 'default', data: { label: 'Node 1' }, position: { x: 0, y: 0 }, style: { background: '#1f2937', color: '#f9fafb', fontSize: 12, padding: 6, borderRadius: 6, width: 100 } },
  { id: '2', type: 'default', data: { label: 'Node 2' }, position: { x: 200, y: 100 }, style: { background: '#1f2937', color: '#f9fafb', fontSize: 12, padding: 6, borderRadius: 6, width: 100 } },
]

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#60a5fa', strokeWidth: 2 }, data: { input: 'default', output: 'default' } },
]

export const ReactFlowGraphView: React.FC<ReactFlowGraphViewProps> = ({ devMode = false }) => {
  const [nodes, setNodes] = useState<Node[]>(initialNodes)
  const [edges, setEdges] = useState<Edge[]>(initialEdges)
  const [selectedElement, setSelectedElement] = useState<Node | Edge | null>(null)

  const onConnect = useCallback((connection: Connection) => setEdges((eds) => addEdge({ ...connection, animated: true, style: { stroke: '#60a5fa' }, data: { input: 'default', output: 'default' } }, eds)), [])

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => setSelectedElement(node), [])
  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => setSelectedElement(edge), [])

  const onLoad = useCallback((rf: OnLoadParams) => rf.fitView(), [])

  // Control Panel
  const ControlPanel: React.FC = () => {
    if (!selectedElement) return null
    const isNode = 'data' in selectedElement

    if (isNode) {
      return (
        <div className="absolute top-4 right-4 z-50 bg-gray-800 text-white p-3 rounded-lg shadow-lg w-64">
          <h3 className="font-bold mb-2">Node Configuration</h3>
          <label className="block text-sm mb-1">Label</label>
          <input
            type="text"
            className="w-full p-1 rounded text-black mb-2"
            value={selectedElement.data.label}
            onChange={(e) => {
              const newLabel = e.target.value
              setNodes((nds) => nds.map((n) => (n.id === selectedElement.id ? { ...n, data: { ...n.data, label: newLabel } } : n)))
            }}
          />

          <h4 className="font-semibold mt-2 mb-1">Connected Edges</h4>
          {edges.filter((ed) => ed.source === selectedElement.id || ed.target === selectedElement.id).map((ed) => (
            <div key={ed.id} className="mb-1 border-b border-gray-600 pb-1">
              <div className="text-xs mb-1">Edge: {ed.id}</div>
              <label className="text-xs">Input</label>
              <input
                type="text"
                className="w-full p-1 rounded text-black mb-1"
                value={ed.data?.input || ''}
                onChange={(e) =>
                  setEdges((eds) =>
                    eds.map((edge) => (edge.id === ed.id ? { ...edge, data: { ...edge.data, input: e.target.value } } : edge))
                  )
                }
              />
              <label className="text-xs">Output</label>
              <input
                type="text"
                className="w-full p-1 rounded text-black"
                value={ed.data?.output || ''}
                onChange={(e) =>
                  setEdges((eds) =>
                    eds.map((edge) => (edge.id === ed.id ? { ...edge, data: { ...edge.data, output: e.target.value } } : edge))
                  )
                }
              />
            </div>
          ))}
          <button className="bg-red-600 px-2 py-1 rounded hover:bg-red-700 mt-2 text-sm" onClick={() => setSelectedElement(null)}>
            Close
          </button>
        </div>
      )
    }

    // Edge selected
    return (
      <div className="absolute top-4 right-4 z-50 bg-gray-800 text-white p-3 rounded-lg shadow-lg w-64">
        <h3 className="font-bold mb-2">Edge Configuration</h3>
        <label className="block text-sm mb-1">Edge ID</label>
        <input
          type="text"
          className="w-full p-1 rounded text-black mb-2"
          value={selectedElement.id}
          onChange={(e) => setEdges((eds) => eds.map((ed) => (ed.id === selectedElement.id ? { ...ed, id: e.target.value } : ed)))}
        />
        <label className="block text-xs">Input</label>
        <input
          type="text"
          className="w-full p-1 rounded text-black mb-1"
          value={selectedElement.data?.input || ''}
          onChange={(e) =>
            setEdges((eds) =>
              eds.map((ed) => (ed.id === selectedElement.id ? { ...ed, data: { ...ed.data, input: e.target.value } } : ed))
            )
          }
        />
        <label className="block text-xs">Output</label>
        <input
          type="text"
          className="w-full p-1 rounded text-black"
          value={selectedElement.data?.output || ''}
          onChange={(e) =>
            setEdges((eds) =>
              eds.map((ed) => (ed.id === selectedElement.id ? { ...ed, data: { ...ed.data, output: e.target.value } } : ed))
            )
          }
        />
        <button className="bg-red-600 px-2 py-1 rounded hover:bg-red-700 mt-2 text-sm" onClick={() => setSelectedElement(null)}>
          Close
        </button>
      </div>
    )
  }

  return (
    <ReactFlowProvider>
      <div className="w-full h-full bg-gray-900 rounded-lg border border-gray-700 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onConnect={devMode ? onConnect : undefined}
          nodesDraggable={true}       
          nodesConnectable={devMode}
          zoomOnScroll
          panOnDrag
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
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
        <ControlPanel />
      </div>
    </ReactFlowProvider>
  )
}

export default ReactFlowGraphView
