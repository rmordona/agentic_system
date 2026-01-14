// src/api/agents.ts
import { api, ApiError } from '@/api/client'

// ✅ SCHEMA = runtime value → normal import
import { AgentSkillSchema } from './types/agent_skill'
import { AgentContextSchema } from './types/agent_context'

// ✅ TYPES = compile-time only → type import
import type { AgentSkill } from './types/agent_skill'
import type { AgentContext } from './types/agent_context'

export async function listWorkspaceAgents(
  workspaceId: string
): Promise<string[]> {
  if (!workspaceId) {
    throw new Error('workspaceId is required')
  }

  return api.get<string[]>(
    `/workspaces/${encodeURIComponent(workspaceId)}/agents`
  )
}


export async function getAgentSkills(
  workspaceId: string,
  agentName: string
): Promise<AgentSkill | null> {
  if (!workspaceId || !agentName) {
    throw new Error('workspaceId and agentName are required')
  }

  try {
    const data = await api.get<unknown>(
      `/workspaces/${encodeURIComponent(workspaceId)}/agents/${encodeURIComponent(agentName)}/skill.json`
    )

    return api.validateApiResponse(
      AgentSkillSchema,
      data,
      'getAgentSkills'
    )
  } catch (err) {
    const apiErr = err as ApiError

    if (apiErr.status === 404) {
      return null
    }

    throw err
  }
}

// ---------------------------
// List all markdown files for an agent
// ---------------------------
export async function getAgentMarkdownFiles(
  workspaceId: string,
  agentName: string
): Promise<string[]> {
  if (!workspaceId || !agentName) {
    throw new Error('workspaceId and agentName are required')
  }

  try {
    const files: string[] = await api.getJson(
      `/workspaces/${encodeURIComponent(workspaceId)}/agents/${encodeURIComponent(agentName)}/prompts`
    )
    // Filter only .md files
    return files.filter((f) => f.endsWith('.md'))
  } catch (err) {
    const apiErr = err as ApiError
    if (apiErr.status === 404) return []
    throw err
  }
}

// ---------------------------
// Fetch content of a specific markdown file
// ---------------------------
export async function getAgentMarkdownContent(
  workspaceId: string,
  agentName: string,
  filename: string
): Promise<string | null> {
  if (!workspaceId || !agentName || !filename) {
    throw new Error('workspaceId, agentName, and filename are required')
  }

  try {
    return await api.getText(
      `/workspaces/${encodeURIComponent(workspaceId)}/agents/${encodeURIComponent(agentName)}/${encodeURIComponent(filename)}`
    )
  } catch (err) {
    const apiErr = err as ApiError
    if (apiErr.status === 404) return null
    throw err
  }
}

export async function getAgentPrompt(
  workspaceId: string,
  agentName: string
): Promise<string | null> {
  if (!workspaceId || !agentName) {
    throw new Error('workspaceId and agentName are required')
  }

  try {
    return await api.getText(
      `/workspaces/${encodeURIComponent(workspaceId)}/agents/${encodeURIComponent(agentName)}/prompt.md`
    )
  } catch (err) {
    const apiErr = err as ApiError

    if (apiErr.status === 404) {
      return null
    }

    throw err
  }
}

export async function getAgentContext(
  workspaceId: string,
  agentName: string
): Promise<ContextItem[] | null> {
  if (!workspaceId || !agentName) {
    throw new Error('workspaceId and agentName are required')
  }

  try {
    const data = await api.get<unknown>(
      `/workspaces/${encodeURIComponent(workspaceId)}/agents/${encodeURIComponent(agentName)}/context.json`
    )

    // Validate against the schema
    const validated = api.validateApiResponse(
      AgentContextSchema,
      data,
      'getAgentContext'
    )

    // Return just the array of context items
    // Passing a top-level array {[]} instead of { "context" : []}, but that may have
    // problem with zodtoschema
    return validated.context
  } catch (err) {
    const apiErr = err as ApiError

    // 404 = context not defined (valid case)
    if (apiErr.status === 404) {
      return null
    }

    throw err
  }
}