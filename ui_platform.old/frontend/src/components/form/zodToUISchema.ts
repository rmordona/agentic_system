import { z } from 'zod'
import { zodToJsonSchema } from 'zod-to-json-schema'

export function zodToUISchema(zodSchema: z.ZodTypeAny) {
  const jsonSchema = zodToJsonSchema(zodSchema)

  return {
    type: 'object',
    properties: jsonSchema.properties,
    required: jsonSchema.required ?? [],
  }
}

