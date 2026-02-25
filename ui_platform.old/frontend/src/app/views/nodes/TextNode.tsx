// nodes/TextNode.tsx
import React from 'react'
import { Handle, Position, NodeProps } from 'reactflow'

interface TextNodeData {
  title: string
  content: string
}

const TextNode: React.FC<NodeProps<TextNodeData>> = ({ data }) => {
  return (
    <div
      style={{
        borderRadius: '12px',
        overflow: 'hidden',
        backgroundColor: '#111827', // dark body background
        color: '#f9fafb',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.25)',
        minWidth: '300px',
        width: '100%',
        maxWidth: '100%',
        display: 'flex',
        flexDirection: 'column',
        fontFamily: 'Inter, sans-serif',
      }}
    >
      {/* Title bar */}
      <div
        style={{
          backgroundColor: '#2563eb', // blue topbar
          padding: '8px 12px',
          fontWeight: 600,
          fontSize: '16px',
          color: 'white',
          borderBottom: '1px solid #1e40af',
        }}
      >
        {data.title || 'Title'}
      </div>

      {/* Content body */}
      <div
        style={{
          padding: '12px',
          fontSize: '14px',
          lineHeight: 1.5,
          color: '#e5e7eb',
          minHeight: '80px',
          maxHeight: '200px',
          overflowY: 'auto',
        }}
      >
        {data.content || 'This is some sample text content for demonstration purposes. You can replace this with real content from your prompt, skills, or context JSON files.'}
      </div>

      {/* Optional handles for ReactFlow connections */}
      <Handle type="target" position={Position.Top} style={{ background: '#2563eb' }} />
      <Handle type="source" position={Position.Bottom} style={{ background: '#2563eb' }} />
    </div>
  )
}

export default TextNode
