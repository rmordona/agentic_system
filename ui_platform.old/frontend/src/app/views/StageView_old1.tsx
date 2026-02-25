import React, { useEffect, useRef } from 'react'
import { Node, Edge, ReactFlow, ReactFlowProvider, ReactFlowInstance } from 'reactflow'
import 'reactflow/dist/style.css'

interface StageViewProps {
  nodes: Node[]
  edges: Edge[]
  isActive: boolean
  style?: React.CSSProperties
  nodeTypes?: any
}

const StageView: React.FC<StageViewProps> = ({ nodes, edges, isActive, style, nodeTypes }) => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const reactFlowRef = useRef<ReactFlowInstance | null>(null)
  const initialized = useRef(false)

  useEffect(() => {
    if (!isActive || !containerRef.current || !reactFlowRef.current) return

    const container = containerRef.current
    const rfInstance = reactFlowRef.current

    // Fit view only once, after container has real size
    const fitViewOnce = () => {
      if (!initialized.current && container.offsetWidth && container.offsetHeight) {
        rfInstance.fitView({ padding: 0.2 })
        initialized.current = true
      }
    }

    // Wait for first paint to ensure container layout
    requestAnimationFrame(() => requestAnimationFrame(fitViewOnce))

    // Observe resizing
    const observer = new ResizeObserver(fitViewOnce)
    observer.observe(container)

    return () => observer.disconnect()
  }, [isActive, nodes, edges])

  return (
    <div
      ref={containerRef}
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
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onInit={(instance) => (reactFlowRef.current = instance)}
          style={{ width: '100%', height: '100%' }}
        />
      </ReactFlowProvider>
    </div>
  )
}

export default StageView
