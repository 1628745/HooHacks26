import { diffArrays } from 'diff'

import type { Metrics } from '../../lib/api/types'

type Props = {
  fileName: string
  isAnalyzePending: boolean
  hasAnalysis: boolean
  /** Code shown on the left (pre-optimization snapshot when a preview exists). */
  leftCode: string
  /** Code shown on the right (optimized output when a preview exists). */
  rightCode: string
  hasOptimizationPreview: boolean
  metricsBefore: Metrics | undefined
  metricsAfter: Metrics | undefined
  callSitesBefore: string[]
  callSitesAfter: string[] | undefined
}

function formatDelta(before: number, after: number | undefined, decimals?: number): string {
  if (after === undefined || Number.isNaN(after)) return '—'
  const d = after - before
  if (decimals !== undefined) {
    const z = (0).toFixed(decimals)
    const fs = d.toFixed(decimals)
    if (fs === z) return '0'
    return d > 0 ? `+${fs}` : fs
  }
  if (d === 0) return '0'
  return d > 0 ? `+${d}` : `${d}`
}

/** Relative change vs baseline; used for energy delta. */
function formatPercentDelta(before: number, after: number | undefined): string {
  if (after === undefined || Number.isNaN(after)) return '—'
  if (before === 0) return after === 0 ? '0%' : '—'
  const pct = ((after - before) / before) * 100
  const rounded = Math.round(pct * 10) / 10
  if (rounded === 0) return '0%'
  const sign = rounded > 0 ? '+' : ''
  return `${sign}${rounded}%`
}

function buildCallDiffRows(before: string[], after: string[]) {
  const parts = diffArrays(before, after)
  const rows: {
    left?: string
    right?: string
    leftTone: 'rem' | 'ok' | 'empty'
    rightTone: 'add' | 'ok' | 'empty'
  }[] = []
  for (const p of parts) {
    if (p.removed) {
      for (const line of p.value) {
        rows.push({ left: line, leftTone: 'rem', rightTone: 'empty' })
      }
    } else if (p.added) {
      for (const line of p.value) {
        rows.push({ right: line, leftTone: 'empty', rightTone: 'add' })
      }
    } else {
      for (const line of p.value) {
        rows.push({ left: line, right: line, leftTone: 'ok', rightTone: 'ok' })
      }
    }
  }
  return rows
}

export function PipelineCenterPanel({
  fileName,
  isAnalyzePending,
  hasAnalysis,
  leftCode,
  rightCode,
  hasOptimizationPreview,
  metricsBefore,
  metricsAfter,
  callSitesBefore,
  callSitesAfter,
}: Props) {
  const showCompareMetrics = Boolean(metricsBefore && metricsAfter)
  const callRows =
    hasOptimizationPreview && callSitesAfter
      ? buildCallDiffRows(callSitesBefore, callSitesAfter)
      : null

  return (
    <div className="center-panel stack">
      <h2 className="center-panel__title">Analysis & comparison</h2>

      {isAnalyzePending ? (
        <p className="hint">Analyzing pipeline…</p>
      ) : !hasAnalysis ? (
        <p className="hint">
          Click <strong>Analyze Pipeline</strong> to load metrics, invoke sites, and this comparison view.
        </p>
      ) : (
        <>
          <section className="metrics-compare" aria-label="Estimated metrics">
            <div className="metrics-compare__header">
              <span className="metrics-compare__file">{fileName}</span>
              {showCompareMetrics ? (
                <span className="metrics-compare__badge">After optimization preview</span>
              ) : (
                <span className="metrics-compare__badge metrics-compare__badge--muted">Current file</span>
              )}
            </div>
            <table
              className={`metrics-compare__table${showCompareMetrics ? ' metrics-compare__table--compare' : ''}`}
              aria-label="Metrics comparison"
            >
              {showCompareMetrics ? (
                <colgroup>
                  <col className="metrics-compare__col metrics-compare__col--metric" />
                  <col className="metrics-compare__col metrics-compare__col--num" />
                  <col className="metrics-compare__col metrics-compare__col--num" />
                  <col className="metrics-compare__col metrics-compare__col--delta" />
                </colgroup>
              ) : (
                <colgroup>
                  <col className="metrics-compare__col metrics-compare__col--metric" />
                  <col className="metrics-compare__col metrics-compare__col--num" />
                </colgroup>
              )}
              <thead>
                <tr>
                  <th scope="col">Metric</th>
                  <th scope="col">Before</th>
                  {showCompareMetrics ? (
                    <>
                      <th scope="col">After</th>
                      <th scope="col">Δ</th>
                    </>
                  ) : null}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">LLM calls</th>
                  <td>{metricsBefore?.llm_calls ?? '—'}</td>
                  {showCompareMetrics ? (
                    <>
                      <td>{metricsAfter?.llm_calls ?? '—'}</td>
                      <td className="metrics-compare__delta">
                        {formatDelta(metricsBefore?.llm_calls ?? 0, metricsAfter?.llm_calls)}
                      </td>
                    </>
                  ) : null}
                </tr>
                <tr>
                  <th scope="row">Tokens (est.)</th>
                  <td>{metricsBefore?.token_estimate ?? '—'}</td>
                  {showCompareMetrics ? (
                    <>
                      <td>{metricsAfter?.token_estimate ?? '—'}</td>
                      <td className="metrics-compare__delta">
                        {formatDelta(metricsBefore?.token_estimate ?? 0, metricsAfter?.token_estimate)}
                      </td>
                    </>
                  ) : null}
                </tr>
                <tr>
                  <th scope="row">Energy (Wh est.)</th>
                  <td>{metricsBefore?.energy_wh ?? '—'}</td>
                  {showCompareMetrics ? (
                    <>
                      <td>{metricsAfter?.energy_wh ?? '—'}</td>
                      <td className="metrics-compare__delta">
                        {metricsBefore != null && metricsAfter != null
                          ? formatPercentDelta(metricsBefore.energy_wh, metricsAfter.energy_wh)
                          : '—'}
                      </td>
                    </>
                  ) : null}
                </tr>
              </tbody>
            </table>
          </section>

          <section className="code-compare" aria-label="Source comparison">
            <div className="code-compare__headers">
              <div className="code-compare__head">
                {hasOptimizationPreview ? 'Before optimization' : 'Current source'}
              </div>
              <div className="code-compare__head">
                {hasOptimizationPreview ? 'Optimized preview' : 'Same file (no preview yet)'}
              </div>
            </div>
            <div className="code-compare__panes">
              <pre className="code-compare__pre">
                <code>{leftCode}</code>
              </pre>
              <pre className="code-compare__pre">
                <code>{rightCode}</code>
              </pre>
            </div>
          </section>

          <section className="call-stack-section" aria-label="LLM invoke sites">
            <h3 className="call-stack-section__title">Call-stack compression</h3>
            <p className="hint call-stack-section__hint">
              Static analysis lists each <code>.invoke</code> / similar call by expression (AST walk order). When you
              preview an optimization, before and after are diff-aligned.
            </p>
            {callRows && callSitesAfter ? (
              <div className="call-stack-diff">
                <div className="call-stack-diff__colhead">Before ({callSitesBefore.length})</div>
                <div className="call-stack-diff__colhead">After ({callSitesAfter.length})</div>
                {callRows.map((row, i) => (
                  <div key={i} className="call-stack-diff__row">
                    <div
                      className={`call-stack-diff__cell call-stack-diff__cell--left call-stack-diff__cell--${row.leftTone}`}
                    >
                      {row.left ?? '\u00a0'}
                    </div>
                    <div
                      className={`call-stack-diff__cell call-stack-diff__cell--right call-stack-diff__cell--${row.rightTone}`}
                    >
                      {row.right ?? '\u00a0'}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <ol className="call-stack-list">
                {callSitesBefore.length === 0 ? (
                  <li className="hint">No LLM invoke sites detected (or heuristic fallback used for call count).</li>
                ) : (
                  callSitesBefore.map((label, i) => (
                    <li key={`${i}-${label.slice(0, 48)}`} className="call-stack-list__item">
                      <code>{label}</code>
                    </li>
                  ))
                )}
              </ol>
            )}
          </section>
        </>
      )}
    </div>
  )
}
