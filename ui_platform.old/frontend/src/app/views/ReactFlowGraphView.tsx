import React, {
  useState,
  useCallback,
  useRef,
  forwardRef,
  useImperativeHandle,
  useEffect
} from 'react'

import ReactFlow, {
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  Background,
  Controls,
  Edge,
  EdgeChange,
  Node,
  Connection,
  ReactFlowProvider,
  MiniMap,
  NodeChange,
  ReactFlowInstance,
} from 'reactflow'

import 'reactflow/dist/style.css'

import StageViewContainer from './StageViewContainer'
import StepperNode from './nodes/StepperNode'
import AgentNode from './nodes/AgentNode'
import LLMNode from './nodes/LLMNode'
import MemoryNode from './nodes/MemoryNode'
import SkillsNode from './nodes/SkillsNode'
import UserInputNode from './nodes/UserInputNode'
import AIOutputNode from './nodes/AIOutputNode'
import AgentOutputNode from './nodes/AgentOutputNode'

import { StageGraphConfig, BuiltGraph } from '@/components/graph/BuildGraphFromConfig'
import { buildGraphFromConfig } from '@/components/graph/BuildGraphFromConfig'

import { WorkspaceContext } from '@/components/types/WorkspaceContext'

const nodeTypes = {
  StepperNode,
  AgentNode,
  LLMNode,
  MemoryNode,
  SkillsNode,
  UserInputNode,
  AIOutputNode,
  AgentOutputNode,
}

export interface ReactFlowGraphViewHandle {
  addNode: () => void
  loadWorkflow: (workflowJson: StageGraphConfig) => void
}


interface ReactFlowGraphViewProps {
  devMode?: boolean
  workspaceContext: WorkspaceContext
}



export const ReactFlowGraphView = forwardRef<ReactFlowGraphViewHandle, ReactFlowGraphViewProps>(
  ({ devMode = false, workspaceContext }, ref) => {
    // =======================
    // Sample Stage Config
    // =======================
    const stageConfig: StageGraphConfig = {
      stages: [
        {
          name: 'ideation',
          description: 'Generates creative ideas ...',
          allowed_agents: ['optimistic'],
          exit_condition: '...',
          next_stages: ['evaluation'],
          priority: 1,
        },
        {
          name: 'evaluation',
          description: 'Evaluates ideas...',
          allowed_agents: ['critic'],
          exit_condition: '...',
          next_stages: ['synthesis'],
          priority: 1,
        },
        {
          name: 'synthesis',
          description: 'Combines ideas...',
          allowed_agents: ['synthesizer'],
          exit_condition: 'True',
          next_stages: [],
          terminal: true,
        },
      ],
    }

    // ============================
    // Initialize graph state once
    // ============================
    const { nodes: initialNodes, edges: initialEdges, stages: initialStages } =
       buildGraphFromConfig(stageConfig, workspaceContext)

    const [nodes, setNodes] = useState<Node[]>(initialNodes)
    const [edges, setEdges] = useState<Edge[]>(initialEdges)
    const [stages, setStages] = useState<BuiltGraph['stages']>(initialStages)
    const [activeStageId, setActiveStageId] = useState<string | null>(initialStages[0]?.id ?? null)
    const [selectedElement, setSelectedElement] = useState<Node | Edge | null>(null)

    const reactFlowInstance = useRef<ReactFlowInstance | null>(null)
    const wrapperRef = useRef<HTMLDivElement | null>(null)

    // =======================
    // ReactFlow callbacks
    // =======================
    const onNodesChange = useCallback((changes: NodeChange[]) => setNodes(nds => applyNodeChanges(changes, nds)),[])
    const onEdgesChange = useCallback((changes: EdgeChange[]) => setEdges(eds => applyEdgeChanges(changes, eds)),[])
    const onConnect = useCallback(
      (connection: Connection) =>
        setEdges(eds =>
          addEdge(
            {
              ...connection,
              animated: true,
              type: 'bezier',
              markerEnd: { type: 'arrowclosed' },
              style: { stroke: '#60a5fa', strokeWidth: 2 },
            },
            eds
          )
        ),
      []
    )

    // const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => setSelectedElement(node), [])

    const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
      setSelectedElement(node)

      // Sync active stage if node belongs to a stage
      const stage = stages.find(s => s.nodes.some(n => n.id === node.id))
      if (stage) setActiveStageId(stage.id)
    }, [stages])

    const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => setSelectedElement(edge), [])
  
    // =======================
    // Imperative API
    // =======================
    useImperativeHandle(ref, () => ({
      addNode() {
        // Optional: implement dev mode add node
      },
      loadWorkflow(workflowJson: StageGraphConfig, workspaceContext: WorkspaceContext) {
        if (!reactFlowInstance.current) return
 
        const { nodes: newNodes, edges: newEdges, stages: newStages } = buildGraphFromConfig(workflowJson, workspaceContext)

        setNodes(newNodes)
        setEdges(newEdges)
        setStages(newStages)
        setActiveStageId(newStages[0]?.id ?? null)

        reactFlowInstance.current.fitView({ padding: 0.2 })
      },
    }))

    // =======================
    // Render
    // =======================
    return (
      <ReactFlowProvider>
        <div
          ref={wrapperRef}
          className="w-full h-full bg-gray-900 rounded-lg border border-gray-700 relative"
          style={{ overflow: 'visible' }}
        >
          {/* Stage views */}
          <StageViewContainer
            stages={stages}
            activeStageId={activeStageId}
            onStageChange={setActiveStageId}
            devMode={devMode}
            workspaceContext={workspaceContext}
          />
        </div>
      </ReactFlowProvider>
    )
  }
)

export default ReactFlowGraphView
