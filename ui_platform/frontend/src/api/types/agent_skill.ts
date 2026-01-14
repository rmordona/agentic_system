import { z } from 'zod'

// --------------------------------------------
// Tool definition
// --------------------------------------------
const AgentToolSchema = z.object({
  name: z.string(),
  when: z.string().optional(),
})

// --------------------------------------------
// Memory config
// --------------------------------------------
const AgentMemorySchema = z.object({
  semantic: z.boolean().optional(),
  episodic: z.boolean().optional(),
})

// --------------------------------------------
// Rewards config
// --------------------------------------------
const AgentRewardsSchema = z.object({
  enabled: z.boolean(),
  callback: z.string(),
})

// --------------------------------------------
// Execution config
// --------------------------------------------
const AgentExecutionSchema = z.object({
  next_stage: z.string().optional(),
  priority: z.number().optional(),
})

// --------------------------------------------
// Runtime config
// --------------------------------------------
const AgentRuntimeSchema = z.object({
  max_retries: z.number().optional(),
  timeout_seconds: z.number().optional(),
})

// --------------------------------------------
// Validation config
// --------------------------------------------
const AgentValidationSchema = z.object({
  strict: z.boolean().optional(),
  required_keys: z.array(z.string()).optional(),
})

// --------------------------------------------
// Logging config
// --------------------------------------------
const AgentLoggingSchema = z.object({
  enable: z.boolean().optional(),
  level: z.string().optional(),
})

// --------------------------------------------
// Safety config
// --------------------------------------------
const AgentSafetySchema = z.object({
  max_output_length: z.number().optional(),
  banned_phrases: z.array(z.string()).optional(),
})

// --------------------------------------------
// Prompt reference
// --------------------------------------------
const AgentPromptSchema = z.object({
  system: z.string(),
})

// --------------------------------------------
// FINAL: Agent Skill Definition
// --------------------------------------------
export const AgentSkillSchema = z.object({
  name: z.string(),
  description: z.string().optional(),

  role: z.string().optional(),
  llm: z.string().optional(),
  output_mode: z.string().optional(),

  prompt: AgentPromptSchema.optional(),
  output_schema: z.string().optional(),

  memory: AgentMemorySchema.optional(),
  tools: z.array(AgentToolSchema).optional(),
  rewards: AgentRewardsSchema.optional(),
  execution: AgentExecutionSchema.optional(),
  runtime: AgentRuntimeSchema.optional(),
  validation: AgentValidationSchema.optional(),
  logging: AgentLoggingSchema.optional(),
  safety: AgentSafetySchema.optional(),
})

export type AgentSkill = z.infer<typeof AgentSkillSchema>
