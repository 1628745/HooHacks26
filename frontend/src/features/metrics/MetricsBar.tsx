import type { Metrics } from '../../lib/api/types'

type Props = {
  before?: Metrics | null
  after?: Metrics | null
}

export function MetricsBar({ before, after }: Props) {
  return (
    <div className="metrics-grid">
      <div>
        <h3>Before</h3>
        <p>Calls: {before?.llm_calls ?? '-'}</p>
        <p>Tokens: {before?.token_estimate ?? '-'}</p>
        <p>Energy: {before?.energy_wh ?? '-'} Wh</p>
      </div>
      <div>
        <h3>After</h3>
        <p>Calls: {after?.llm_calls ?? '-'}</p>
        <p>Tokens: {after?.token_estimate ?? '-'}</p>
        <p>Energy: {after?.energy_wh ?? '-'} Wh</p>
      </div>
    </div>
  )
}
