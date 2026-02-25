import { NodeProps, Handle, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import '../../styles/user_input.css'

interface UserInputNodeData {
  label?: string
}

const UserInputNode = (props: NodeProps<UserInputNodeData>) => {
  return (
    <div className="user-input-node">
      {/* Transparent icon container */}
      <div className="user-input-node__icon-container">
        <img
          src="/public/images/user_input_icon.png"
          alt="User Input"
          className="user-input-node__icon"
        />

      </div>
      <Handle
        type="source"
        position={Position.Right}
        id="userinput-source"
        className="user-input-node__handle"
        style={{ top: '110px', left: '140px' }}
      />
    </div>
  )
}

export default UserInputNode
