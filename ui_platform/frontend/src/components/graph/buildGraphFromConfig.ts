import { Node, Edge } from 'reactflow'


import { WorkspaceContext } from '@/components/types/WorkspaceContext'

export interface BuiltGraph {
  nodes: Node[]
  edges: Edge[]
  stages: {
    id: string
    name: string
    description?: string
    allowed_agents?: string[]
    exit_condition?: string
    next_stages?: string[]
    terminal?: boolean
    nodes: Node[]
    edges: Edge[]
  }[]
}

export const buildGraphFromConfig = (config: StageGraphConfig, workspaceContext: WorkspaceContext): BuiltGraph => {
  const nodes: Node[] = []
  const edges: Edge[] = []

  const stages = config.stages.map(stage => {
    const stageId = crypto.randomUUID()
    const agentId = `${stageId}:agent`
    const modelId = `${stageId}:model`
    const memoryId = `${stageId}:memory`
    const skillsId = `${stageId}:skills`


    const stageNodes: Node[] = [
      { id: modelId, type: 'LLMNode', position: { x: 50, y: 50 }, 
          data: { workspaceContext } 
      },
      { id: memoryId, type: 'MemoryNode', position: { x: 50, y: 150 }, 
          data: { workspaceContext }  
      },
      {
        id: agentId,
        type: 'AgentNode',
        position: { x: 250, y: 100 },
        data: {
          allowedAgents: stage.allowed_agents,
          exitCondition: stage.exit_condition,
          workspaceContext
        },
      },
      { id: skillsId, type: 'SkillsNode', position: { x: 550, y: 100 }, 
        data: { workspaceContext } 
      },
    ]

    const stageEdges: Edge[] = [
      {
        id: `${agentId}->model`,
        source: agentId,
        target: modelId,
        sourceHandle: `${agentId}-model-source`,
        targetHandle: `${modelId}-model-target`,
        type: 'smoothstep',
        animated: true,
        style: {
          stroke: '#0ff',
          strokeWidth: 2,
          strokeDasharray: '5,5', // dashed line
        },
      },
      {
        id: `${agentId}->memory`,
        source: agentId,
        target: memoryId,
        sourceHandle: `${agentId}-memory-source`,
        targetHandle: `${memoryId}-memory-target`,
        type: 'smoothstep',
        animated: true,
        style: {
          stroke: '#0ff',
          strokeWidth: 2,
          strokeDasharray: '5,5', // dashed line
        },
      },
      {
        id: `${agentId}->skills`,
        source: agentId,
        target: skillsId,
        sourceHandle: `${agentId}-skills-source`,
        targetHandle: `${skillsId}-skills-target`,
        type: 'smoothstep',
        animated: true,
        style: {
          stroke: '#0ff',
          strokeWidth: 2,
          strokeDasharray: '5,5', // dashed line
        },
      },
    ]

    // add stage nodes to global nodes
    nodes.push(...stageNodes)

    // stage edges (can implement your buildStageEdges function here)
    edges.push(...stageEdges)

    return {
      ...stage,
      id: stageId,
      nodes: stageNodes,
      edges: stageEdges,
    }
  })

  // Add your UserInput / AIOutput / Stepper nodes here if needed
  const userInputId = `${crypto.randomUUID()}:userInput`
  const aiOutputId = `${crypto.randomUUID()}:aiOutput`
  nodes.push(
    { id: userInputId, type: 'UserInputNode', position: { x: 700, y: 20 } },
    { id: aiOutputId, type: 'AIOutputNode', position: { x: 700, y: 400 } }
  )

  return { nodes, edges, stages }
}
