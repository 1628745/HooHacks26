export type PipelineNode = {
  id: string
  label: string
  node_type: string
  code_span?: [number, number] | null
  metadata: Record<string, unknown>
  confidence: number
  notes: string[]
}

export type PipelineEdge = {
  source: string
  target: string
}

export type PipelineIR = {
  nodes: PipelineNode[]
  edges: PipelineEdge[]
}

export type Issue = {
  id: string
  issue_type: string
  severity: 'low' | 'medium' | 'high'
  title: string
  description: string
  node_ids: string[]
  suggested_action: string
}

export type Metrics = {
  llm_calls: number
  token_estimate: number
  energy_wh: number
}

export type AnalyzeRequest = {
  file_name: string
  code: string
}

export type AnalyzeResponse = {
  ir: PipelineIR
  issues: Issue[]
  metrics_before: Metrics
  parser_notes: string[]
}

export type OptimizeRequest = {
  file_name: string
  original_code: string
  ir: PipelineIR
  selected_issue_ids?: string[]
}

export type OptimizeResponse = {
  optimized_code: string
  issues_applied: string[]
  explanation: string
  metrics_before: Metrics
  metrics_after: Metrics
  diff_hunks: string[]
  llm_used?: boolean
  optimization_event_log?: string[]
}

export type ChatMessage = {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export type ChatRequest = {
  file_name: string
  current_code: string
  messages: ChatMessage[]
}

export type ChatResponse = {
  assistant_message: string
  updated_code?: string | null
  llm_used?: boolean
}

export type ValidateResponse = {
  valid: boolean
  errors: string[]
}
