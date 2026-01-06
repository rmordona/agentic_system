// src/app/loaders/WorkspaceLoader.ts
import { redirect } from 'react-router-dom'
import { api } from '@/api/client'
import { isAuthenticated } from '../auth'

export async function fetchWorkspaceLoader({ params }: { params: any }) {
  if (!isAuthenticated()) {
    return redirect('/login')
  }

  const { workspaceId } = params
  if (!workspaceId) {
    throw new Response('Workspace ID missing', { status: 400 })
  }

  try {
    // Fetch workspace data from API
    const workspace = await api.getWorkspace(workspaceId)
    return workspace // returned data is accessible via useLoaderData()
  } catch (err: any) {
    throw new Response(err.message || 'Failed to load workspace', { status: 500 })
  }
}
