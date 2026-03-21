import axios from 'axios'
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

export async function validateCode(code: string): Promise<ValidateResponse> {
  const { data } = await api.post<ValidateResponse>('/api/pipeline/validate', { code })
  return data
}

export async function chatWithAssistant(payload: ChatRequest): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/api/pipeline/chat', payload)
  return data
}
