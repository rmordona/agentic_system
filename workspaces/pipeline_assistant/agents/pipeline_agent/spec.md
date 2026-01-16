## Specification

- The agent must produce a JSON object.
- The object must contain keys: `id`, `status`, `result`.
- `status` must be one of: "success", "failure".
- If status = "failure", `result` must contain an error message.
- Output must be deterministic given identical inputs.

