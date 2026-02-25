import React, { useRef, useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import ReactFlowGraphView, {
  ReactFlowGraphViewHandle,
} from './ReactFlowGraphView'

// Import the CSS for the bottom panel
import './../styles/bottom-text-panel.css'

import { WorkspaceContext } from '@/components/types/WorkspaceContext'

import { loadAgentAssets } from '@/app/loaders/loadAgentAssets'

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

const GraphEditorView: React.FC<{ mode: 'user' | 'developer' }> = ({ mode }) => {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const graphRef = useRef<ReactFlowGraphViewHandle>(null)

  const [showLoadPanel, setShowLoadPanel] = useState(false)
  const [workflowPath, setWorkflowPath] = useState<string>('workflows/sampleWorkflow.json')
  const [loadedWorkflowName, setLoadedWorkflowName] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  // -----------------------------
  // Bottom panel text states
  // -----------------------------
  const [promptText, setPromptText] = useState('Loading prompt.md...')
  const [skillsText, setSkillsText] = useState('Loading skills.json...')
  const [contextText, setContextText] = useState('Loading context.json...')

  // -----------------------------
  // Set Workspace Context
  // -----------------------------
  const [workspaceContext, setWorkspaceContext] = useState<WorkspaceContext | null>(null)

  useEffect(() => {
    if (!workspaceId) return

    let cancelled = false

    async function loadContext() {
      try {
        const agents = await loadAgentAssets(workspaceId)

        if (!cancelled) {
          setWorkspaceContext({
            workspaceId,
            agents,
          })
        }
      } catch (err) {
        console.error('Failed to load workspace context', err)
      }
    }

    loadContext()

    return () => {
      cancelled = true
    }
  }, [workspaceId])

  // Render guards
  if (!workspaceContext) {
    return <div>Loading workspace…</div>
  }


  // -----------------------------
  // Workflow JSON validation
  // -----------------------------
  const validateWorkflowJson = (json: any): json is StageGraphConfig => {
    if (!json || typeof json !== 'object') {
      setLoadError('Workflow JSON is not an object.')
      return false
    }
    if (!Array.isArray(json.stages)) {
      setLoadError('Missing "stages" array in workflow JSON.')
      return false
    }
    for (const [index, stage] of json.stages.entries()) {
      if (typeof stage.name !== 'string') {
        setLoadError(`Stage #${index + 1} is missing a valid "name".`)
        return false
      }
      if (!Array.isArray(stage.allowed_agents)) {
        setLoadError(`Stage "${stage.name}" has invalid or missing "allowed_agents".`)
        return false
      }
      if (typeof stage.exit_condition !== 'string') {
        setLoadError(`Stage "${stage.name}" has invalid or missing "exit_condition".`)
        return false
      }
      if (!Array.isArray(stage.next_stages)) {
        setLoadError(`Stage "${stage.name}" has invalid or missing "next_stages".`)
        return false
      }
    }

    setLoadError(null)
    return true
  }

  // -----------------------------
  // Load Workflow Handler
  // -----------------------------
  const handleLoad = async () => {
    try {
      const response = await fetch(`/${workflowPath}`)
      if (!response.ok) throw new Error(`Workflow not found at ${workflowPath}`)

      const workflowJson = await response.json()
      if (!validateWorkflowJson(workflowJson)) return

      graphRef.current?.loadWorkflow(workflowJson)

      const parts = workflowPath.split('/')
      setLoadedWorkflowName(parts[parts.length - 1])
      setShowLoadPanel(false)
      setLoadError(null)
    } catch (err: any) {
      console.error('Failed to load workflow:', err)
      setLoadError(err.message || 'Failed to load workflow. Check console.')
    }
  }

  // -----------------------------
  // Render
  // -----------------------------
  return (
    <div className="flex h-full w-full bg-blue-50 dark:bg-blue-900 rounded-lg overflow-hidden">
      {/* Left Graph Controls */}
      <div className="w-64 bg-blue-100 dark:bg-blue-800 p-4 border-r dark:border-blue-700 relative">
        <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-3">Graph Controls</h3>
        <ul className="space-y-2 text-sm text-blue-800 dark:text-blue-200">
          <li className="cursor-pointer" onClick={() => graphRef.current?.addNode()}>
            Add Node  
          </li>
          <li>Add Edge</li>
          <li>Validate Graph Configuration</li>
          <li>Save Graph Configuration</li>
          <li
            className="cursor-pointer text-blue-700 dark:text-blue-200 mt-4"
            onClick={() => setShowLoadPanel(prev => !prev)}
          >
            Load Graph Configuration
          </li>
        </ul>

        {showLoadPanel && (
          <div className="absolute top-24 left-4 w-56 p-4 bg-white/90 dark:bg-gray-800/90 border border-gray-300 dark:border-gray-600 rounded shadow-lg z-50">
            <h4 className="font-semibold mb-2 text-gray-900 dark:text-gray-100">Workflow JSON</h4>
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">Path to workflow file:</p>
            <input
              type="text"
              value={workflowPath}
              onChange={e => setWorkflowPath(e.target.value)}
              className="w-full p-1 rounded border border-gray-300 dark:border-gray-600 text-black dark:text-white mb-2"
            />
            <button
              className="w-full bg-blue-600 dark:bg-blue-700 text-white p-1 rounded hover:bg-blue-700 dark:hover:bg-blue-600"
              onClick={handleLoad}
            >
              Load
            </button>
            {loadError && (
              <div className="mt-2 p-2 bg-red-100 dark:bg-red-800 text-red-800 dark:text-red-100 text-sm rounded border border-red-300 dark:border-red-700">
                <strong>Error:</strong> {loadError}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right panel: ReactFlow + bottom text panel */}
      <div className="flex-1 flex flex-col p-6 bg-white dark:bg-gray-900">
        <h2 className="text-2xl font-bold mb-2 text-gray-900 dark:text-gray-100">Graph Editor</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
          Workspace ID: <strong>{workspaceId}</strong>
        </p>
        {loadedWorkflowName && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Loaded Workflow: <strong>{loadedWorkflowName}</strong>
          </p>
        )}

        {/* Main content container */}
        <div className="flex-1 flex flex-col rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-700 overflow-hidden">
          {/* ReactFlow Graph (top 80%) */}
          <div className="flex-[0_0_80%]">
            <ReactFlowGraphView ref={graphRef} devMode={true}  workspaceContext={workspaceContext}/>
          </div>

          {/* Bottom Text Panel (20%) */}
          <div className="bottom-panel flex-[0_0_20%] flex">
            {/* Prompt.md (60%) */}
            <div className="panel prompt">
              <div className="panel-title">Prompt.md</div>
              <div className="panel-content">{promptText}</div>
            </div>

            {/* Skills.json (20%) */}
            <div className="panel skills">
              <div className="panel-title">Skills.json</div>
              <div className="panel-content">{skillsText}</div>
            </div>

            {/* Context.json (20%) */}
            <div className="panel context">
              <div className="panel-title">Context.json</div>
              <div className="panel-content">{contextText}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default GraphEditorView
