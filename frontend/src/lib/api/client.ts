import axios, { isAxiosError } from 'axios'
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ChatRequest,
  ChatResponse,
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
