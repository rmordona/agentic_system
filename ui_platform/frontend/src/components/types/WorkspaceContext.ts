export interface GraphContext {
  workspaceId: string
  mode: 'user' | 'developer'
  agents?: any[] // optional, can grow later
}

