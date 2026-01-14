import {
  listWorkspaceAgents,
  getAgentSkills,
  getAgentPrompt,
  getAgentContext,
} from '@/api/agents'

interface AgentAssets {
  name: string
  skills: any | null
  prompt: string | null
  context: any | null
}

export async function loadAgentAssets(
  workspaceId: string
): Promise<AgentAssets[]> {
  const agentNames = await listWorkspaceAgents(workspaceId)

  return Promise.all(
    agentNames.map(async (name) => {
      const [skills, prompt, context] = await Promise.all([
        getAgentSkills(workspaceId, name),
        getAgentPrompt(workspaceId, name),
        getAgentContext(workspaceId, name),
      ])

      return {
        name,
        prompt,
        skills,
        context,
      }
    })
  )
}
