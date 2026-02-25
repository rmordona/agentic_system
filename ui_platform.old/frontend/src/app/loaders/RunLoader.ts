import { api } from '@/api/client'

export async function fetchRunLoader({ params }: any) {
  const runId = params.runId
  return api.getRun(runId) // stub for now
}

