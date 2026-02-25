import React from 'react'
import { NodeProps, Handle, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import '../../styles/stage-node.css'

interface StageNodeData {
  label: string
  description?: string
}

const StageNode = ({ id, data, selected }: NodeProps<StageNodeData>) => {
  return (
    <div className={`stage-node ${selected ? 'is-selected' : ''}`}>
      {/* Shell for overflow control */}
      <div className="stage-node__shell">
        
        {/* Top bar: badge + title */}
        <div className="stage-node__topbar">
          <span className="stage-node__badge">STAGE</span>
          <span className="stage-node__title-text">{data.title}</span>
        </div>

        {/* Optional description below top bar */}
        {data.description && (
          <div className="stage-node__description">{data.description}</div>
        )}

        {/* Body container for child nodes */}
        <div className="stage-node__body" />

        {/* Handles for edges */}
        <Handle
          type="target"
          position={Position.Left}
          id={`${id}-target`}
          className="stage-node__handle"
          style={{ top: '80px', left: '-5px' }}
        />
        <Handle
          type="source"
          position={Position.Left}
          id={`${id}-source`}
          className="stage-node__handle"
          style={{ top: '200px', left: '-5px' }}
        />
      </div>
    </div>
  )
}

export default StageNode
