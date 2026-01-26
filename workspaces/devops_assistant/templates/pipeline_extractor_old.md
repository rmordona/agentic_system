# SPEC-DRIVEN DEVELOPMENT PIPELINE JSON EXTRACTOR (qwen2-Optimized)

## INSTRUCTIONS

You are an AI pipeline extractor. Your task is to generate a **single, fully valid JSON object** representing the Spec-Driven Development (SDD) pipeline described below.  

Because some models like qwen2 may struggle with strict JSON rules, follow this **step-by-step approach internally**, but produce only the **final JSON object** as output.  

Do NOT include:
- Markdown
- Code fences
- Comments
- Explanations
- Any text outside JSON

The first character must be `{` and the last must be `}`.

---

## EXTRACTION CONTRACT (STRICT)

1. The JSON must have the following structure:

{
  "stages": [
    {
      "name": "string",
      "description": "string",
      "allowed_agents": ["string"],
      "exit_condition": "string | null",
      "next_stages": [
        {
          "name": "string",
          "condition": "string | null"
        }
      ],
      "terminal": boolean
    }
  ]
}

2. **Closed stage set**: Only these stages are valid:
   - spec_check
   - clarification
   - ideation
   - judgment
   - validation
   - spec_revision
   - approval
   - block
   - terminal

3. **Stage order**: Emit stages in the order they appear in the template. Each stage must appear exactly once.

4. **Field rules**:
   - `allowed_agents`: default to `[]` if none specified
   - `exit_condition`: default to `null` if none specified
   - `next_stages`: must be `[]` if none specified or if the stage is terminal
   - `terminal`: `true` only for terminal stages; otherwise `false`

5. **Conditions**:
   - Allowed only in `exit_condition` or `next_stages[].condition`
   - Never put condition symbols in `next_stages[].name`

6. **Terminal stages**:
   - `terminal: true`
   - `exit_condition: null`
   - `next_stages: []`


{{PIPELINE_MARKDOWN}}


## qwen2-SPECIFIC INSTRUCTIONS

Because qwen2 may forget commas, default fields, or terminal rules:

1. **Fill all fields** for every stage: `name`, `description`, `allowed_agents`, `exit_condition`, `next_stages`, `terminal`
2. **Default empty fields** correctly:
   - `allowed_agents: []`  
   - `exit_condition: null`  
   - `next_stages: []` (especially for terminal stages)
3. **Never put conditions in `next_stages.name`** — only in `.condition`
4. **Terminal stage** must have `terminal: true`, `exit_condition: null`, and `next_stages: []`
5. Ensure **all arrays and objects are properly closed**, no trailing commas
6. **Output only JSON**, nothing else

---

## OUTPUT

Output a **single JSON object** containing the pipeline stages according to the above rules.
