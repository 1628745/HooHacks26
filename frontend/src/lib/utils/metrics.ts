import type { Metrics } from '../api/types'

export function formatMetrics(metrics: Metrics | null | undefined): string {
  if (!metrics) {
    return 'No metrics yet'
  }
  return `${metrics.llm_calls} calls · ${metrics.token_estimate} tokens · ${metrics.energy_wh.toFixed(2)} Wh`
}
