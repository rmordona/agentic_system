import React, {
  useState,
  useCallback,
  useRef,
  forwardRef,
  useImperativeHandle,
  useEffect,
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

import NodeControlPanelView from './NodeControlPanelView'
import EdgeControlPanelView from './EdgeControlPanelView'

import { StageGraphConfig } from '../utils/workflowToGraph'

/* =======================
   Node imports
======================= */

import StageViewContainer from './StageViewContainer' 
import StepperNode from './nodes/StepperNode'
import AgentNode from './nodes/AgentNode'
import LLMNode from './nodes/LLMNode'
import MemoryNode from './nodes/MemoryNode'
import SkillsNode from './nodes/SkillsNode'
import UserInputNode from './nodes/UserInputNode'
import AIOutputNode from './nodes/AIOutputNode'
import AgentOutputNode from './nodes/AgentOutputNode'

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
}

/* =======================
   Build graph from config
======================= */
const buildStageEdges = (stage: any, stageIdByName: any, activeStageId?: string): Edge[] => {

    const stageId = stageIdByName.get(stage.name)!

    const isActive = stageId === activeStageId

    const agentId = `${stageId}:agent`
    const modelId = `${stageId}:model`
    const memoryId = `${stageId}:memory`
    const skillsId = `${stageId}:skills`

    // Use the node's id as a prefix
    const modelTarget = `${modelId}-model-target`
    const memoryTarget = `${memoryId}-memory-target`
    const skillsTarget = `${skillsId}-skills-target`
    const agentModelSource = `${agentId}-model-source`
    const agentMemorySource = `${agentId}-memory-source`
    const agentSkillsSource = `${agentId}-skills-source`

    console.log("Model Target: ", modelTarget)
    console.log("Memory Target: ", memoryTarget)
    console.log("Skills Target: ", skillsTarget)
    console.log("AgenetModelSource", agentModelSource)
    console.log("agentMemorySource", agentMemorySource)
    console.log("agentSkillsSource", agentSkillsSource)

  return [
    {
      id: `${stageId}-agent-to-model`,
      source: agentId,
      sourceHandle: agentModelSource,
      target: modelId,
      targetHandle: modelTarget,
      type: 'smoothstep',
      animated: isActive,
      style: {
        stroke: '#0ff',
        strokeWidth: 2,
        //opacity: isActive ? 1 : 0.3,
      },
    },
    {
      id: `${stageId}-agent-to-memory`,
      source: agentId,
      sourceHandle: agentMemorySource,
      target: memoryId,
      targetHandle: memoryTarget,
      type: 'smoothstep',
      animated: isActive,
      zIndex: 1000,
      style: {
        stroke: '#0ff',
        strokeWidth: 2,
        //opacity: isActive ? 1 : 0.3,
      },
    },
    {
      id: `${stageId}-agent-to-skills`,
      source: agentId,
      sourceHandle: agentSkillsSource,
      target: skillsId,
      targetHandle: skillsTarget,
      type: 'smoothstep',
      animated: isActive,
      style: {
        stroke: '#0ff',
        strokeWidth: 2,
        //opacity: isActive ? 1 : 0.3,
      },
    },
  ]
}


const buildGraphFromConfig = (config: StageGraphConfig) => {
  const nodes: Node[] = []
  const edges: Edge[] = []

  const stepperId = `stepper-${crypto.randomUUID()}`

  // Map stage name → stageId
  const stages = config.stages.map(stage => ({
    ...stage,
    id: crypto.randomUUID(),
  }))
  const initialStageId = stages.length > 0 ? stages[0].id : undefined

  // ---------- UserInput & AIOutput ----------
  const userInputId = `${crypto.randomUUID()}:userInput`
  const aiOutputId = `${crypto.randomUUID()}:aiOutput`

  // 🔑 Map stage name → stageId so we can link stages safely
  const stageIdByName = new Map<string, string>()

  // ---------- FIRST PASS: create stage IDs ----------
  config.stages.forEach((stage) => {
    stageIdByName.set(stage.name, crypto.randomUUID())
  })

  nodes.push(
    { id: userInputId, type: 'UserInputNode', position: { x: 700, y: 20 } },
    { id: aiOutputId, type: 'AIOutputNode', position: { x: 700, y: 400 } }
  )

  // ---------- StepperNode ----------
  if (stages.length > 0 && initialStageId) {

    // UserInput → StepperNode
    edges.push({
      id: `${userInputId}-to-stepper`,
      source: userInputId,
      sourceHandle: 'userinput-source',
      target: stepperId,
      targetHandle: `${stepperId}-target`,
      type: 'smoothstep',
      animated: true,
      markerEnd: { type: 'arrowclosed' },
      style: { stroke: '#60a5fa', strokeWidth: 2 },
    })

    // StepperNode → first stage (handled internally)
    edges.push({
      id: `${stepperId}-to-first-stage`,
      source: stepperId,
      sourceHandle: `${stepperId}-source`,
      target: aiOutputId, // just placeholder; StepperNode handles StageNode rendering
      targetHandle: 'aioutput-target',
      type: 'smoothstep',
      animated: true,
      markerEnd: { type: 'arrowclosed' },
      style: { stroke: '#60a5fa', strokeWidth: 2 },
    })
  
  }
  
  stages.forEach(stage => {

    const stageId = stageIdByName.get(stage.name)!

    const agentId = `${stageId}:agent`
    const modelId = `${stageId}:model`
    const memoryId = `${stageId}:memory`
    const skillsId = `${stageId}:skills`

    const nodes = [
      { id: agentId, type: 'AgentNode', position: { x: 250, y: 100 } },
      { id: modelId, type: 'LLMNode', position: { x: 50, y: 50 } },
      { id: memoryId, type: 'MemoryNode', position: { x: 50, y: 150 } },
      { id: skillsId, type: 'SkillsNode', position: { x: 450, y: 100 } }
    ]
    const edges = buildStageEdges(stage, stageIdByName, true) // or false for inactive
  })
  

  return { nodes, edges }
}

/* =======================
   Sample stage config
======================= */
const stageConfig: StageGraphConfig = {
  stages: [
    { name: 'ideation', description: 'Generates creative ideas ...', allowed_agents: ['optimistic'], exit_condition: '...', next_stages: ['evaluation'], priority: 1 },
    { name: 'evaluation', description: 'Evaluates ideas...', allowed_agents: ['critic'], exit_condition: '...', next_stages: ['synthesis'], priority: 1 },
    { name: 'synthesis', description: 'Combines ideas...', allowed_agents: ['synthesizer'], exit_condition: 'True', next_stages: [], terminal: true },
  ],
}

const { nodes: initialNodes, edges: initialEdges } = buildGraphFromConfig(stageConfig)

/* =======================
   ReactFlowGraphView
   with StepperNode + StageViews
======================= */
export const ReactFlowGraphView = forwardRef<ReactFlowGraphViewHandle, ReactFlowGraphViewProps>(
  ({ devMode = false }, ref) => {
    const [nodes, setNodes] = useState<Node[]>(initialNodes)
    const [edges, setEdges] = useState<Edge[]>(initialEdges)
    const [selectedElement, setSelectedElement] = useState<Node | Edge | null>(null)

    // --- Track active stage and stage data ---
    const [stages, setStages] = useState(stageConfig.stages.map(stage => ({
      ...stage,
      id: crypto.randomUUID(),
      nodes: [
        { id: `${crypto.randomUUID()}:model`, type: 'LLMNode', position: { x: 50, y: 50 } },
        { id: `${crypto.randomUUID()}:memory`, type: 'MemoryNode', position: { x: 50, y: 150 } },
        { id: `${crypto.randomUUID()}:agent`, type: 'AgentNode', position: { x: 250, y: 100 } },
        { id: `${crypto.randomUUID()}:skills`, type: 'SkillsNode', position: { x: 450, y: 100 } },
      ],
      edges: [], // will compute later if needed
    })))
    const [activeStageId, setActiveStageId] = useState(stages[0]?.id)

    const reactFlowInstance = useRef<ReactFlowInstance | null>(null)
    const wrapperRef = useRef<HTMLDivElement | null>(null)

    const onNodesChange = useCallback((changes: NodeChange[]) => setNodes(nds => applyNodeChanges(changes, nds)), [])
    const onEdgesChange = useCallback((changes: EdgeChange[]) => setEdges(eds => applyEdgeChanges(changes, eds)), [])
    const onConnect = useCallback((connection: Connection) =>
      setEdges(eds => addEdge({ ...connection, animated: true, type: 'bezier', markerEnd: { type: 'arrowclosed' }, style: { stroke: '#60a5fa', strokeWidth: 2 } }, eds)), [])

    const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => setSelectedElement(node), [])
    const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => setSelectedElement(edge), [])

    useImperativeHandle(ref, () => ({
      addNode() {},
      loadWorkflow(workflowJson: StageGraphConfig) {
        if (!reactFlowInstance.current) return
        const rf = reactFlowInstance.current
        const { nodes: newNodes, edges: newEdges } = buildGraphFromConfig(workflowJson)
        setNodes(newNodes)
        setEdges(newEdges)
        // reset stages dynamically
   
        const newStages = workflowJson.stages.map(stage => ({
          ...stage,
          id: crypto.randomUUID(),
          nodes: [
            { id: `${crypto.randomUUID()}:model`, type: 'LLMNode', position: { x: 50, y: 50 } },
            { id: `${crypto.randomUUID()}:memory`, type: 'MemoryNode', position: { x: 50, y: 150 } },
            { id: `${crypto.randomUUID()}:agent`, type: 'AgentNode', position: { x: 250, y: 100 } },
            { id: `${crypto.randomUUID()}:skills`, type: 'SkillsNode', position: { x: 450, y: 100 } },
          ],
          edges: [], 
        }))
        
        setStages(newStages)
        setActiveStageId(newStages[0]?.id)
   
        rf.fitView({ padding: 0.2 })
      },
    }))

    return (
      <ReactFlowProvider>
        <div ref={wrapperRef} className="w-full h-full bg-gray-900 rounded-lg border border-gray-700 relative" style={{ overflow: 'visible' }}>
          
          {/* --- StageViewContainer handles Stepper + StageViews --- */}
          <StageViewContainer stages={stages} />


          {/* --- Original ReactFlow Graph --- */}
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onInit={(instance) => {
              reactFlowInstance.current = instance
              instance.setViewport({ x: 30, y: 30, zoom: 1.2 })
            }}
            defaultEdgeOptions={{ zIndex: 10 }}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={devMode ? onConnect : undefined}
            nodesDraggable
            nodesConnectable={devMode}
            zoomOnScroll
            panOnDrag
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            style={{ fontSize: 12, overflow: 'visible' }}
          >
            <Background gap={16} size={1} color="#374151" />
            <MiniMap
              nodeStrokeColor={(n) => (n.style?.background as string) || '#374151'}
              nodeColor={(n) => (n.style?.background as string) || '#1f2937'}
              nodeBorderRadius={6}
            />
            <Controls />
          </ReactFlow>

          {/* --- Node/Edge Control Panels --- */}
          {/*
          {selectedElement && isNode(selectedElement) && (
            <NodeControlPanelView
              selectedElement={selectedElement}
              nodes={nodes}
              edges={edges}
              setNodes={setNodes}
              setEdges={setEdges}
              setSelectedElement={setSelectedElement}
            />
          )}

          {selectedElement && isEdge(selectedElement) && (
            <EdgeControlPanelView
              edge={selectedElement}
              setEdges={setEdges}
              onClose={() => setSelectedElement(null)}
            />
          )}
          */}
        </div>
      </ReactFlowProvider>
    )
  }
)

export default ReactFlowGraphView
