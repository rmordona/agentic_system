import { Node, Edge } from 'reactflow'

export interface WorkflowStage {
  id: string
  name: string
  allowed_agents: string[]
  exit_condition: string
  next_stages: string[]
  priority?: number
  terminal?: boolean
}

export interface WorkflowConfig {
  stages: WorkflowStage[]
}

export function workflowToGraph(config: WorkflowConfig): {
  nodes: Node[]
  edges: Edge[]
} {
  const nodes: Node[] = []
  const edges: Edge[] = []

  const xSpacing = 260
  const y = 140

  config.stages.forEach((stage, index) => {
    nodes.push({
      id: stage.id,
      type: 'default',
      position: { x: index * xSpacing, y },
      data: {
        label: stage.name,
        workflow: stage, // 🔑 attach full JSON
      },
      style: {
        background: '#1f2937',
        color: '#f9fafb',
        fontSize: 12,
        padding: 6,
        borderRadius: 6,
        width: 160,
      },
    })

    stage.next_stages.forEach((targetId) => {
      edges.push({
        id: `${stage.id}-${targetId}`,
        source: stage.id,
        target: targetId,
        animated: true,
        type: 'smoothstep',
        markerEnd: { type: 'arrowclosed' },
        style: { stroke: '#60a5fa', strokeWidth: 2 },
      })
    })
  })

  return { nodes, edges }
}

