import React from 'react'
import { Node } from 'reactflow'

interface NodeProfileViewProps {
  node: Node
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>
}

const NodeProfileView: React.FC<NodeProfileViewProps> = ({ node }) => {
  const stage = node.data?.stageConfig

  if (!stage) {
    return (
      <div className="text-sm text-gray-400">
        No stage metadata available.
      </div>
    )
  }

  return (
    <div className="space-y-4 text-sm">
      <div>
        <label className="block mb-1 font-medium">Stage Name</label>
        <input
          className="w-full p-1 rounded text-black"
          value={stage.name}
          readOnly
        />
      </div>

      <div>
        <label className="block mb-1 font-medium">Allowed Agents</label>
        <select className="w-full p-1 rounded text-black">
          {stage.allowed_agents.map((agent: string) => (
            <option key={agent}>{agent}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block mb-1 font-medium">Exit Condition</label>
        <textarea
          className="w-full p-1 rounded text-black"
          value={stage.exit_condition}
          rows={3}
          readOnly
        />
      </div>

      <div>
        <label className="block mb-1 font-medium">Next Stages</label>
        <select className="w-full p-1 rounded text-black">
          {stage.next_stages.length === 0 ? (
            <option>None</option>
          ) : (
            stage.next_stages.map((next: string) => (
              <option key={next}>{next}</option>
            ))
          )}
        </select>
      </div>

      <div className="flex items-center gap-2">
        <input type="checkbox" checked={!!stage.terminal} readOnly />
        <span>Terminal Stage</span>
      </div>
    </div>
  )
}

export default NodeProfileView
