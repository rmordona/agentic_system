// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/store/runStore.ts
//
// Description:
//   Zustand store for managing workflow/agent runs and observability of
//   prompt inputs and outputs. Supports real-time updates and SSE integration.
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

import { create } from 'zustand'

export interface RunEntry {
  id: string
  timestamp: string
  nodeId: string
  input: string
  output?: string
  metadata?: Record<string, any>
}

export interface RunState {
  runs: RunEntry[]
  addRun: (run: RunEntry) => void
  updateRunOutput: (id: string, output: string) => void
  clearRuns: () => void
}

export const useRunStore = create<RunState>((set) => ({
  runs: [],

  /** Add a new run entry */
  addRun: (run) => set((state) => ({ runs: [...state.runs, run] })),

  /** Update the output of an existing run entry */
  updateRunOutput: (id, output) =>
    set((state) => ({
      runs: state.runs.map((r) => (r.id === id ? { ...r, output } : r)),
    })),

  /** Clear all run entries */
  clearRuns: () => set({ runs: [] }),
}))
