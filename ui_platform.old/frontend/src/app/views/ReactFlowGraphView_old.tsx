import React, {
  useState,
  useCallback,
  useRef,
  forwardRef,
  useImperativeHandle,
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
import StageNode from './nodes/StageNode'
import AgentNode from './nodes/AgentNode'
import LLMNode from './nodes/LLMNode'
import MemoryNode from './nodes/MemoryNode'
import SkillsNode from './nodes/SkillsNode'
import UserInputNode from './nodes/UserInputNode'
import AIOutputNode from './nodes/AIOutputNode'
import AgentOutputNode from './nodes/AgentOutputNode'

const nodeTypes = {
  StageNode,
  AgentNode,
  LLMNode,
  MemoryNode,
  SkillsNode,
  UserInputNode,
  AIOutputNode,
  AgentOutputNode
}

export interface ReactFlowGraphViewHandle {
  addNode: () => void
  loadWorkflow: (workflowJson: StageGraphConfig) => void
}

interface ReactFlowGraphViewProps {
  devMode?: boolean
}

interface StageConfig {
  name: string
  allowed_agents: string[]
  exit_condition: string
  next_stages: string[]
  priority?: number
  terminal?: boolean
}

interface StageGraphConfig {
  stages: StageConfig[]
}

/* =======================
   Build graph from config
======================= */
const buildGraphFromConfig = (config: StageGraphConfig) => {
  const nodes: Node[] = []
  const edges: Edge[] = []

  const x = 220
  const ySpacing = 420
  const stage_last_index = config.stages.length-1

  // 🔑 Map stage name → stageId so we can link stages safely
  const stageIdByName = new Map<string, string>()

  // ---------- FIRST PASS: create stage IDs ----------
  config.stages.forEach((stage) => {
    stageIdByName.set(stage.name, crypto.randomUUID())
  })

  // ---------- SECOND PASS: build nodes + edges ----------

  // Build first the User input and AI output

  const userInputId = `${crypto.randomUUID()}:userInput`
  const aiOutputId = `${crypto.randomUUID()}:aiOutput`

  // User Input
  const userInputNode: Node = {
    id: userInputId,
    type: 'UserInputNode',
    position: { x: 40, y: 20 },
    // style: { overflow: 'visible', pointerEvents: 'auto' },
  }

  // Agent Output
  const aiOutputNode: Node = {
    id: aiOutputId,
    type: 'AIOutputNode',
    position: { x: 40, y: 4 * 320 },
    // style: { overflow: 'visible', pointerEvents: 'auto' },
  }

  nodes.push(userInputNode, aiOutputNode)

  config.stages.forEach((stage, index) => {

    const stageId = stageIdByName.get(stage.name)!

    const agentId = `${stageId}:agent`
    const modelId = `${stageId}:model`
    const memoryId = `${stageId}:memory`
    const skillsId = `${stageId}:skills`
    const agentoutputId = `${stageId}:agentoutput`

    // Use the node's id as a prefix
    const modelTarget = `${modelId}-model-target`
    const memoryTarget = `${memoryId}-memory-target`
    const skillsTarget = `${agentId}-skills-target`
    const agentModelSource = `${agentId}-model-source`
    const agentMemorySource = `${agentId}-memory-source`
    const agentSkillsSource = `${agentId}-skills-source`
    
    // StageNode (parent)
    const stageNode: Node = {
      id: stageId,
      type: 'StageNode',
      position: { x, y: index * ySpacing },
      data: { title: stage.name, description: stage.description },
      style: {
        width: 600,
        height: 380,
        background: '#111827',
        overflow: 'visible',
        pointerEvents: 'none',
        zIndex: 'auto'
      },
    }

    // AgentNode
    const agentNode: Node = {
      id: agentId,
      type: 'AgentNode',
      parentNode: stageId,
      extent: 'parent',
      position: { x: 150, y: 135 },
      data: {
        title: stage.name,
        fields: [{ label: 'Agents', value: stage.allowed_agents.join(', ') }],
      },
      style: { overflow: 'visible',pointerEvents: 'auto' },
    }

    // LLMNode
    const modelNode: Node = {
      id: modelId,
      type: 'LLMNode',
      parentNode: stageId,
      extent: 'parent',
      position: { x: 40, y: 120 },
      style: { overflow: 'visible', pointerEvents: 'auto' },
    }

    // MemoryNode
    const memoryNode: Node = {
      id: memoryId,
      type: 'MemoryNode',
      parentNode: stageId,
      extent: 'parent',
      position: { x: 40, y: 200 },
      style: { overflow: 'visible', pointerEvents: 'auto' },
    }


      // SkillsNode
    const skillsNode: Node = {
      id: skillsId,
      type: 'SkillsNode',
      parentNode: stageId,
      extent: 'parent',
      position: { x: 360, y: 100 },
      style: { overflow: 'visible', pointerEvents: 'auto' },
    }

    // Agent Output
    const agentOutputNode: Node = {
      id: agentoutputId,
      type: 'agentOutputNode',
      width: '300px',
      height: '400px',
      position: { x: 40, y: 420 },
      position: { x:40 , y: index * ySpacing },
      data: { title: stage.name, description: stage.description },
      style: {
        background: '#111827',
        overflow: 'visible',
        pointerEvents: 'none',
        zIndex: 'auto'
      },
    }


    nodes.push(stageNode, agentNode, modelNode, memoryNode, skillsNode, agentOutputNode)

    // ---------- Internal edges ----------
    
    // connect agent to model
    edges.push({
      id: `${agentId}-model-${crypto.randomUUID()}`,
      source: agentId,
      sourceHandle: agentModelSource,
      target: modelId,
      targetHandle: modelTarget,
      type: 'smoothstep',
      animated: true,
      markerEnd: { type: 'arrowclosed' },
      style: { stroke: '#35659fff', strokeWidth: 1, strokeDasharray: "2, 4", zIndex: 100 },
    })

    // connect agent to memory
    edges.push({
      id: `${agentId}-memory-${crypto.randomUUID()}`,
      source: agentId,
      sourceHandle: agentMemorySource,
      target: memoryId,
      targetHandle: memoryTarget,
      type: 'smoothstep',
      animated: true,
      markerEnd: { type: 'arrowclosed' },
      style: { stroke: '#35659fff', strokeWidth: 1, strokeDasharray: "2, 4",  zIndex: 100 },
    })

    // connect agent to skills
    edges.push({
      id: `${agentId}-skillbook-${crypto.randomUUID()}`,
      source: agentId,
      sourceHandle: agentSkillsSource,
      target: skillsId,
      targetHandle: skillsTarget,
      type: 'smoothstep',
      animated: true,
      markerEnd: { type: 'arrowclosed' },
      style: { stroke: '#35659fff', strokeWidth: 1, strokeDasharray: "2, 4",  zIndex: 100 },
    })
      console.log("Index:", index)

    // connect user input to first stage
    if (index == 0) {
      console.log("Index Here:", index)
      edges.push({
        id: `userinput-handle-${crypto.randomUUID()}`,
        source: userInputId,
        sourceHandle: "userinput-source",
        target: stageId,
        targetHandle: `${stageId}-target`,
        type: 'smoothstep',
        animated: true,
        markerEnd: { type: 'arrowclosed' },
        style: { stroke: '#35659fff', strokeWidth: 1, strokeDasharray: "2, 4", zIndex: 100 },
      })
    }

    if (index == stage_last_index) {
      console.log("Index Here:", index)
      edges.push({
        id: `aioutput-handle-${crypto.randomUUID()}`,
        source: stageId,
        sourceHandle: `${stageId}-target`,
        target: aiOutputId,
        targetHandle: "aioutput-target",
        type: 'smoothstep',
        animated: true,
        markerEnd: { type: 'arrowclosed' },
        style: { stroke: '#35659fff', strokeWidth: 1, strokeDasharray: "2, 4", zIndex: 100 },
      })
    }
    console.log("length:", index, stage_last_index )

    // ---------- Agent → next stage Agent ----------

    const targets = new Set<string>()

    // Explicit next_stages
    stage.next_stages.forEach((next) => {
      // Only connect to StageNode inside the group
      const nextStageNodeId = next
      if (nodes.find((n) => n.id === nextStageNodeId)) {
        targets.add(nextStageNodeId)
      }
    })

    // Fallback sequential edge
    if (targets.size === 0 && index < config.stages.length - 1) {
      targets.add(config.stages[index + 1].name)
    }

    // Push edges from this StageNode → next StageNode(s)
    targets.forEach((target) => {
      const nextStageId = stageIdByName.get(target)
      edges.push({
        id: `${stageId}-${target}-${crypto.randomUUID()}`,
        source: stageId,      // StageNode inside the group
        sourceHandle: `${stageId}-source`,   // must match the StageNode's source handle
        target: nextStageId,               // StageNode in next group
        targetHandle: `${nextStageId}-target`, // must match the next StageNode's target handle
        type: 'smoothstep',
        animated: true,
        markerEnd: { type: 'arrowclosed' },
        style: { stroke: '#35659fff', strokeWidth: 1, strokeDasharray: "2, 4", },
      })
    })
      
  })

  return { nodes, edges }
}


/* =======================
   Sample stage config
======================= */
const stageConfig: StageGraphConfig = {
  stages: [
    {
      name: 'ideation',
      description: 'Generates creative ideas ...',
      allowed_agents: ['optimistic'],
      exit_condition: "...",
      next_stages: ['evaluation'],
      priority: 1,
    },
    {
      name: 'evaluation',
      description: 'Evaluates ideas...',
      allowed_agents: ['critic'],
      exit_condition: "...",
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

const { nodes: initialNodes, edges: initialEdges } = buildGraphFromConfig(stageConfig)

/* =======================
   ReactFlowGraphView
======================= */
export const ReactFlowGraphView = forwardRef<
  ReactFlowGraphViewHandle,
  ReactFlowGraphViewProps
>(({ devMode = false }, ref) => {
  const [nodes, setNodes] = useState<Node[]>(initialNodes)
  const [edges, setEdges] = useState<Edge[]>(initialEdges)
  const [selectedElement, setSelectedElement] = useState<Node | Edge | null>(null)

  const reactFlowInstance = useRef<ReactFlowInstance | null>(null)
  const wrapperRef = useRef<HTMLDivElement | null>(null)

  /* =======================
     Callbacks
  ======================= */
  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((nds) => applyNodeChanges(changes, nds))
  }, [])

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((eds) => applyEdgeChanges(changes, eds))
  }, [])

  const onConnect = useCallback(
    (connection: Connection) =>
      setEdges((eds) =>
        addEdge(
          { ...connection,
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

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => setSelectedElement(node), [])
  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => setSelectedElement(edge), [])

  const isNode = (el: Node | Edge): el is Node => (el as Node).position !== undefined
  const isEdge = (el: Node | Edge): el is Edge => (el as Edge).source !== undefined && (el as Edge).target !== undefined

  /* =======================
     Exposed API
  ======================= */
  useImperativeHandle(ref, () => ({
    addNode() { /* unchanged */ },
    loadWorkflow(workflowJson: StageGraphConfig) {
      if (!reactFlowInstance.current) return
      const rf = reactFlowInstance.current
      const { nodes: newNodes, edges: newEdges } = buildGraphFromConfig(workflowJson)
      setNodes(newNodes)
      setEdges(newEdges)
      rf.fitView({ padding: 0.2 })
    },
  }))

  /* =======================
     Render
  ======================= */
  return (
    <ReactFlowProvider>
      <div
        ref={wrapperRef}
        className="w-full h-full bg-gray-900 rounded-lg border border-gray-700 relative"
        style={{ overflow: 'visible' }} // ✅ allow edges to render outside
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onInit={(instance) => {
            reactFlowInstance.current = instance
             console.log(instance.getNodes(), instance.getEdges())
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
          style={{ fontSize: 12, overflow: 'visible' }} // ✅ ensure container allows overflow
        >
          <Background gap={16} size={1} color="#374151" />
          <MiniMap
            nodeStrokeColor={(n) => (n.style?.background as string) || '#374151'}
            nodeColor={(n) => (n.style?.background as string) || '#1f2937'}
            nodeBorderRadius={6}
          />
          <Controls />
        </ReactFlow>

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
      </div>
    </ReactFlowProvider>
  )
})

export default ReactFlowGraphView
