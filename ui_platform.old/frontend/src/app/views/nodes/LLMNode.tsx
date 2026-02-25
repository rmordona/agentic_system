import { NodeProps, Handle, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import '../../styles/icon-node.css'

interface LLMNodeProps {
  data?: {}
}

const LLMNode = (props: NodeProps<LLMNodeData>) => {
  return (
    <div className="icon-node icon-node--llm">
      {/* ICON CONTAINER */}
      <div className="icon-node__circle">
        <img
          src="/images/llm_icon.png"
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
        id={`${props.id}-model-target`} // e.g., modelId-handle
        className="icon-node__handle"
      />
    </div>
  )
}

export default LLMNode
