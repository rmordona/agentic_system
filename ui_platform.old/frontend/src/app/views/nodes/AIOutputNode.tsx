import { NodeProps, Handle, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import '../../styles/ai_output.css'

interface AIOutputNodeData {
  label?: string
}

const AIOutputNode = (props: NodeProps<AIOutputNodeData>) => {
  return (
    <div className="ai-output-node">
      {/* Transparent icon container */}
      <div className="ai-output-node__icon-container">
        <img
          src="/public/images/ai_output_icon.png"
          alt="AI Output"
          className="ai-output-node__icon"
        />
      </div>
      {/* Target handle */}
      <Handle
        type="target"
        position={Position.Right}
        id="aioutput-target"
        className="ai-output-node__handle"
        style={{ top: '65px', left: '120px' }}
      />
    </div>
  )
}

export default AIOutputNode
