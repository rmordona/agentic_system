// buildStageEdges.ts
import { Edge } from 'reactflow'

interface BuildStageEdgesParams {
  stageId: string
  isActive: boolean
}

export function buildStageEdges({
  stageId,
  isActive,
}: BuildStageEdgesParams): Edge[] {
  const edgeClass = isActive ? 'edge-active' : 'edge-inactive'

  return [
    {
      id: `${stageId}-model-agent`,
      source: `${stageId}-model`,
      sourceHandle: `${stageId}-model-target`,
      target: `${stageId}-agent`,
      targetHandle: `${stageId}-model-source`,
      animated: isActive,
      className: edgeClass,
    },
    {
      id: `${stageId}-memory-agent`,
      source: `${stageId}-memory`,
      sourceHandle: `${stageId}-memory-target`,
      target: `${stageId}-agent`,
      targetHandle: `${stageId}-memory-source`,
      animated: isActive,
      className: edgeClass,
    },
    {
      id: `${stageId}-agent-skills`,
      source: `${stageId}-agent`,
      sourceHandle: `${stageId}-skills-source`,
      target: `${stageId}-skills`,
      targetHandle: `${stageId}-skills-target`,
      animated: isActive,
      className: edgeClass,
    },
  ]
}

