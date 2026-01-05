// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/store/workspaceStore.ts
//
// Description:
//   Zustand store for managing workspaces, including creation, selection,
//   and metadata. Supports developer and user view modes.
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

import { create } from 'zustand'

export interface Workspace {
  id: string
  name: string
  description?: string
  createdAt: string
  updatedAt?: string
  stages?: any[] // optional array of stages for graph building
}

export type ViewMode = 'user' | 'developer'

export interface WorkspaceState {
  workspaces: Workspace[]
  currentWorkspaceId?: string
  viewMode: ViewMode
  setWorkspaces: (workspaces: Workspace[]) => void
  selectWorkspace: (id: string) => void
  setViewMode: (mode: ViewMode) => void
  updateWorkspace: (id: string, data: Partial<Workspace>) => void
  addWorkspace: (workspace: Workspace) => void
  removeWorkspace: (id: string) => void
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  workspaces: [],
  currentWorkspaceId: undefined,
  viewMode: 'user',

  /** Set the list of workspaces */
  setWorkspaces: (workspaces) => set({ workspaces }),

  /** Select a workspace by ID */
  selectWorkspace: (id) => set({ currentWorkspaceId: id }),

  /** Set the view mode (developer/user) */
  setViewMode: (mode) => set({ viewMode: mode }),

  /** Update workspace data by ID */
  updateWorkspace: (id, data) =>
    set((state) => ({
      workspaces: state.workspaces.map((ws) =>
        ws.id === id ? { ...ws, ...data, updatedAt: new Date().toISOString() } : ws
      ),
    })),

  /** Add a new workspace */
  addWorkspace: (workspace) =>
    set((state) => ({ workspaces: [...state.workspaces, workspace] })),

  /** Remove a workspace by ID */
  removeWorkspace: (id) =>
    set((state) => ({
      workspaces: state.workspaces.filter((ws) => ws.id !== id),
      currentWorkspaceId:
        state.currentWorkspaceId === id ? undefined : state.currentWorkspaceId,
    })),
}))
