import { NodeProps, Handle, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import '../../styles/icon-node.css'

interface AgentOutputNodeProps {
  data?: {}
}

const AgentOutputNode = (props: NodeProps<AgentOutputodeData>) => {
  return (
    <div className="icon-node icon-node--llm">
      {/* ICON CONTAINER */}
      <div className="icon-node__circle">
        <img
          src="/public/images/agent_output_icon.png"
          alt="LLM"
          className="icon-node__icon"
        />
      </div>

      {/* LABEL */}
      <div className="icon-node__label">Model</div>

      {/* HANDLES */}
      <Handle
        type="target"
        position={Position.Right}
        id={`${props.id}-agentoutput-target`} // e.g., modelId-handle
        className="icon-node__handle"
      />
    </div>
  )
}

export default AgentOutputNode
