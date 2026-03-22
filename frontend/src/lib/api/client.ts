import axios, { isAxiosError } from 'axios'
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ChatRequest,
  ChatResponse,
  OptimizePanelEntry,
  OptimizeRequest,
  OptimizeResponse,
  ValidateResponse,
} from './types'

// Must be >= backend OPENROUTER_TIMEOUT_SECONDS so optimize/chat can wait for slow models.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  timeout: 600_000, // 10 minutes (ms)
})

export async function analyzePipeline(payload: AnalyzeRequest): Promise<AnalyzeResponse> {
  const { data } = await api.post<AnalyzeResponse>('/api/pipeline/analyze', payload)
  return data
}

export async function optimizePipeline(payload: OptimizeRequest): Promise<OptimizeResponse> {
  const { data } = await api.post<OptimizeResponse>('/api/pipeline/optimize', payload)
  return data
}

const apiBase = () => import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type OptimizeStreamHandlers = {
  onLog: (level: 'info' | 'ok' | 'error', message: string) => void
  onDone: (payload: OptimizeResponse) => void
  onFatal: (detail: { message: string; optimization_event_log?: string[] }) => void
}

/**
 * POST /optimize-stream (SSE). Invokes onLog for each backend LLM/progress line as it arrives.
 */
export async function optimizePipelineStream(
  payload: OptimizeRequest,
  handlers: OptimizeStreamHandlers,
): Promise<void> {
  const res = await fetch(`${apiBase()}/api/pipeline/optimize-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    let detail: { message: string; optimization_event_log?: string[] } = {
      message: `Optimization failed (${res.status})`,
    }
    try {
      const body = await res.json()
      const d = body?.detail
      if (typeof d === 'string') {
        detail = { message: d }
      } else if (d && typeof d === 'object') {
        const o = d as { message?: string; optimization_event_log?: string[] }
        detail = {
          message: o.message ?? detail.message,
          optimization_event_log: o.optimization_event_log,
        }
      }
    } catch {
      /* ignore */
    }
    handlers.onFatal(detail)
    return
  }

  const reader = res.body?.getReader()
  if (!reader) {
    handlers.onFatal({ message: 'No response body from optimize stream' })
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''
  let terminal = false

  const handleEvent = (obj: Record<string, unknown>) => {
    if (obj.event === 'log') {
      const level = obj.level
      const message = obj.message
      if (
        (level === 'info' || level === 'ok' || level === 'error') &&
        typeof message === 'string'
      ) {
        handlers.onLog(level, message)
      }
    } else if (obj.event === 'done' && obj.payload && typeof obj.payload === 'object') {
      if (terminal) {
        return
      }
      terminal = true
      handlers.onDone(obj.payload as OptimizeResponse)
    } else if (obj.event === 'fatal' && obj.detail && typeof obj.detail === 'object') {
      if (terminal) {
        return
      }
      terminal = true
      const d = obj.detail as { message?: string; optimization_event_log?: string[] }
      handlers.onFatal({
        message: d.message ?? 'Optimization failed',
        optimization_event_log: d.optimization_event_log,
      })
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''
    for (const block of parts) {
      const trimmed = block.trim()
      if (!trimmed.startsWith('data:')) {
        continue
      }
      const payloadLine = trimmed.startsWith('data: ') ? trimmed.slice(6) : trimmed.slice(5)
      try {
        handleEvent(JSON.parse(payloadLine) as Record<string, unknown>)
      } catch {
        if (!terminal) {
          terminal = true
          handlers.onFatal({ message: `Bad SSE payload: ${payloadLine.slice(0, 120)}` })
        }
        return
      }
    }
  }

  if (!terminal) {
    handlers.onFatal({ message: 'Connection closed before optimization finished.' })
  }
}

export function fatalDetailToEntries(detail: {
  message: string
  optimization_event_log?: string[]
}): OptimizePanelEntry[] {
  const out: OptimizePanelEntry[] = []
  if (detail.optimization_event_log?.length) {
    for (const line of detail.optimization_event_log) {
      out.push({ level: 'error', line })
    }
  }
  if (detail.message) {
    out.push({ level: 'error', line: detail.message })
  }
  return out
}

export function axiosErrorToEntries(err: unknown): OptimizePanelEntry[] {
  return linesFromOptimizeAxiosError(err).map((line) => ({ level: 'error' as const, line }))
}

/** Lines to show under the optimize buttons when a request fails (502, network, etc.). */
export function linesFromOptimizeAxiosError(err: unknown): string[] {
  if (!isAxiosError(err)) {
    return [err instanceof Error ? err.message : String(err)]
  }
  const raw = err.response?.data as { detail?: unknown } | undefined
  const d = raw?.detail
  if (typeof d === 'string') {
    return [d]
  }
  if (Array.isArray(d)) {
    return d.map((x) => String(x))
  }
  if (d && typeof d === 'object') {
    const o = d as { message?: string; optimization_event_log?: string[] }
    const lines: string[] = []
    if (o.optimization_event_log?.length) {
      lines.push(...o.optimization_event_log)
    }
    if (o.message) {
      lines.push(o.message)
    }
    if (lines.length) {
      return lines
    }
  }
  return [err.message || 'Optimization request failed']
}

export async function validateCode(code: string): Promise<ValidateResponse> {
  const { data } = await api.post<ValidateResponse>('/api/pipeline/validate', { code })
  return data
}

export async function chatWithAssistant(payload: ChatRequest): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/api/pipeline/chat', payload)
  return data
}
