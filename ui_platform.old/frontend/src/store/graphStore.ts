// -----------------------------------------------------------------------------
// Project: Agentic System UI Platform
// File: ui_platform/frontend/src/app/components/store/graphStore.ts
//
// Description:
//   Zustand store for managing graphs and their nodes/edges.
//   Supports creation, update, deletion of nodes/edges and observability of workflow graphs.
//
// Author: Raymond M.O. Ordona
// Created: 2026-01-04
// -----------------------------------------------------------------------------

import { create } from 'zustand'

export interface Node {
  id: string
  label: string
  type?: string
  data?: any
}

export interface Edge {
  id: string
  source: string
  target: string
  label?: string
  data?: any
}

export interface GraphState {
  nodes: Node[]
  edges: Edge[]
  addNode: (node: Node) => void
  updateNode: (id: string, data: Partial<Node>) => void
  removeNode: (id: string) => void
  addEdge: (edge: Edge) => void
  updateEdge: (id: string, data: Partial<Edge>) => void
  removeEdge: (id: string) => void
  clearGraph: () => void
}

export const useGraphStore = create<GraphState>((set) => ({
  nodes: [],
  edges: [],

  /** Add a new node to the graph */
  addNode: (node) => set((state) => ({ nodes: [...state.nodes, node] })),

  /** Update an existing node by ID */
  updateNode: (id, data) =>
    set((state) => ({
      nodes: state.nodes.map((n) => (n.id === id ? { ...n, ...data } : n)),
    })),

  /** Remove a node by ID */
  removeNode: (id) =>
    set((state) => ({
      nodes: state.nodes.filter((n) => n.id !== id),
      edges: state.edges.filter((e) => e.source !== id && e.target !== id), // remove connected edges
    })),

  /** Add a new edge to the graph */
  addEdge: (edge) => set((state) => ({ edges: [...state.edges, edge] })),

  /** Update an existing edge by ID */
  updateEdge: (id, data) =>
    set((state) => ({
      edges: state.edges.map((e) => (e.id === id ? { ...e, ...data } : e)),
    })),

  /** Remove an edge by ID */
  removeEdge: (id) =>
    set((state) => ({
      edges: state.edges.filter((e) => e.id !== id),
    })),

  /** Clear all nodes and edges */
  clearGraph: () => set({ nodes: [], edges: [] }),
}))
