import React from 'react'
import { NodeProps, Handle, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import '../../styles/icon-node.css'
import '../../styles/agent-node.css'
 
interface AgentNodeProps {
  data?: {} // optional
}

const AgentNode = ({ id, data, selected }: NodeProps<AgentNodeProps>) => {
  return (
    <div className={`agent-node ${selected ? 'is-selected' : ''}`}>
      {/* Use the shell div for proper overflow and pointer-events */}
      <div className="agent-node__shell">
        {/* ICON */}
        <div className="icon-node__skill_manager_circle">
          <img
            src="/images/skill_manager_icon.png"
            alt="Tools"
            className="icon-node__skill_manager_icon"
          />
        </div>

        {/* Title */}
        <div className="agent-node__title">
          Skill Manager
        </div>

        {/* Handles */}
        <Handle
          type="source"
          position={Position.Left}
          id={`${id}-model-source`} // e.g., agentId-to-model
          className="icon-node__handle"
          style={{ top: '20px' }} // 80px from top
        />
        <Handle
          type="source"
          position={Position.Left}
          id={`${id}-memory-source`} // e.g., agentId-to-memory
          className="icon-node__handle"
          style={{ top: '100px' }} // 80px from top
        />
        <Handle
          type="source"
          position={Position.Right}
          id={`${id}-skills-source`} // e.g., agentId-to-memory
          className="icon-node__handle"
        />
      </div>
    </div>
  )
}

export default AgentNode
