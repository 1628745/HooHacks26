# API Contract

## `GET /api/health`
- Response: `{ "status": "ok" }`

## `POST /api/pipeline/analyze`
- Request:
  - `file_name: string`
  - `code: string`
- Response:
  - `ir: { nodes, edges }`
  - `issues: Issue[]`
  - `metrics_before: Metrics`
  - `parser_notes: string[]`

## `POST /api/pipeline/optimize`
- Request:
  - `file_name: string`
  - `original_code: string`
  - `ir: PipelineIR`
  - `selected_issue_ids?: string[]`
- Response:
  - `optimized_code: string`
  - `issues_applied: string[]`
  - `explanation: string`
  - `metrics_before: Metrics`
  - `metrics_after: Metrics`
  - `diff_hunks: string[]`
  - `llm_used: boolean` — `true` when `OPENROUTER_API_KEY` is set and OpenRouter returned code; otherwise deterministic rewrite.

## `POST /api/pipeline/chat`
- Requires **`OPENROUTER_API_KEY`**. Returns **503** if not configured.
- Request:
  - `file_name: string`
  - `current_code: string`
  - `messages: { role: string, content: string }[]`
- Response:
  - `assistant_message: string`
  - `updated_code?: string` — if the model returned a valid ```python block
  - `llm_used: boolean`

## `POST /api/pipeline/validate`
- Request:
  - `code: string`
- Response:
  - `valid: boolean`
  - `errors: string[]`
