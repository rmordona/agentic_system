import { z } from 'zod'

// -----------------------------
// Single context item schema
// -----------------------------
export const ContextItemSchema = z.object({
  name: z.string(),
  type: z.enum(['text', 'state', 'memory', 'external', 'computed']),
  // Only for text type
  text: z.string().optional(),
  // Only for memory type
  memory_type: z.enum(['semantic', 'episodic']).optional(),
  // Filters can include top_k, agent, or other keys
  filters: z
    .object({
      top_k: z.number().optional(),
      agent: z.string().optional(),
      // allow other keys as well
    })
    .passthrough()
    .optional(),
  // Only for external type
  service: z.string().optional(),
  namespace: z.string().optional(),
  // Only for computed type
  function: z.string().optional(),
})

// -----------------------------
// Full context schema
// -----------------------------
export const AgentContextSchema = z.object({
  context: z.array(ContextItemSchema),
})

// -----------------------------
// Type inference
// -----------------------------
export type ContextItem = z.infer<typeof ContextItemSchema>
export type AgentContext = z.infer<typeof AgentContextSchema>
