import { useEffect, useState } from 'react'
import { NodeProps, Handle, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import '../../styles/icon-node.css'

import { loadAgentAssets } from '@/app/loaders/loadAgentAssets'

import { WorkspaceContext } from '@/components/types/WorkspaceContext'

import SkillPanelView from '../SkillPanelView'

const SkillsNode: React.FC<NodeProps<SkillsNodeData>> = ({ id, data }) => {
  const { workspaceContext } = data

  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null)

  const workspaceId = workspaceContext.workspaceId // set from buildGraphFromConfig.ts

  const [agents, setAgents] = useState<AgentAssets[]>([])

  useEffect(() => {
    if (!workspaceId) return

    loadAgentAssets(workspaceId)
      .then(setAgents)
      .catch(err => {
        console.error(err)
        setAgents([]) // RESET grid if loading fails
      })
  }, [workspaceId])

  return (
    <div className="icon-node icon-node--skills">
      {/* GRID */}
      <div className="icon-node__skills-grid">
        {agents.map((agent, index) => (
          <div
            key={agent.name}
            className="icon-node__skills_circle"
            title={agent.name} // ✅ tooltip
            onClick={() => setSelectedSkill(agent)}
          >
            <img
              src="/images/tools_icon.png"
              alt={agent.name}
              className="icon-node__skills_icon"
            />
          </div>
        ))}
      <Handle
        type="target"
        position={Position.Left}
        id={`${id}-skills-target`}
        className="icon-node__handle"
        style={{ top: '40px' }}
      />
      </div>

      {/* LABEL */}
      <div className="icon-node__label">
        {data?.title ?? 'Skills Book'}
      </div>

      {/* MAIN TARGET HANDLE */}

      {selectedSkill && (
        <SkillPanelView
          skillName={selectedSkill.name}
          prompt={selectedSkill.prompt}
          skillJson={selectedSkill.skills}
          contextJson={selectedSkill.context}
          onClose={() => setSelectedSkill(null)}
        />
      )}

    </div>
  )
}

export default SkillsNode
