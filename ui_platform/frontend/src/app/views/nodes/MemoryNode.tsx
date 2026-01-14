import { NodeProps, Handle, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import '../../styles/icon-node.css'

interface MemoryNodeProps {
  data?: {}
}

const MemoryNode = (props: NodeProps<MemoryNodeData>) => {

  return (
    <div className="icon-node icon-node--memory">
      {/* ICON CONTAINER */}
      <div className="icon-node__circle">
        <img
          src="/images/memory_icon.png"
          alt="Memory"
          className="icon-node__icon"
        />
      </div>

      {/* LABEL */}
      <div className="icon-node__label">Memory</div>

      {/* HANDLES */}
      <Handle
        type="target"
        position={Position.Right}
        id={`${props.id}-memory-target`} // e.g., memoryId-handle
        className="icon-node__handle"
      />

    </div>
  )
}

export default MemoryNode
