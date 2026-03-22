import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'

import { ThreePanelLayout } from './layout/ThreePanelLayout'
import { OptimizationAssistantPanel } from '../features/assistant/OptimizationAssistantPanel'
import { CodeEditorPanel } from '../features/code/CodeEditorPanel'
import { DiffPreviewModal } from '../features/diff/DiffPreviewModal'
import { PipelineGraphPanel } from '../features/graph/PipelineGraphPanel'
import { MetricsBar } from '../features/metrics/MetricsBar'
import { FileUploadPanel } from '../features/upload/FileUploadPanel'
import {
  analyzePipeline,
  axiosErrorToEntries,
  fatalDetailToEntries,
  optimizePipelineStream,
} from '../lib/api/client'
import { usePipelineStore } from '../lib/state/usePipelineStore'

export default function App() {
  const store = usePipelineStore()
  const [optimizePending, setOptimizePending] = useState(false)

  const analyze = useMutation({
    mutationFn: analyzePipeline,
    onSuccess: (data) => {
      store.setAnalysis(data)
      store.setOptimization(null)
      store.setOptimizePanelEntries([])
    },
  })

  const runOptimize = async () => {
    if (!store.analysis) {
      return
    }
    setOptimizePending(true)
    store.setOptimizePanelEntries([])
    try {
      await optimizePipelineStream(
        {
          file_name: store.fileName,
          original_code: store.currentCode,
          ir: store.analysis.ir,
        },
        {
          onLog: (level, message) => {
            store.setOptimizePanelEntries((prev) => [...prev, { level, line: message }])
          },
          onDone: (data) => {
            store.setOptimization(data)
            store.setShowDiff(true)
          },
          onFatal: (detail) => {
            store.setOptimizePanelEntries((prev) => [...prev, ...fatalDetailToEntries(detail)])
          },
        },
      )
    } catch (err) {
      store.setOptimizePanelEntries((prev) => [...prev, ...axiosErrorToEntries(err)])
    } finally {
      setOptimizePending(false)
    }
  }

  return (
    <>
      <ThreePanelLayout
        left={
          <div className="stack">
            <FileUploadPanel
              onLoad={(name, content) => {
                store.setFileName(name)
                store.setOriginalCode(content)
                store.setCurrentCode(content)
                store.setAnalysis(null)
                store.setOptimization(null)
                store.setOptimizePanelEntries([])
              }}
            />
            <CodeEditorPanel value={store.currentCode} onChange={store.setCurrentCode} />
            <div className="actions">
              <button
                onClick={() => analyze.mutate({ file_name: store.fileName, code: store.currentCode })}
                disabled={analyze.isPending}
              >
                {analyze.isPending ? 'Analyzing...' : 'Analyze Pipeline'}
              </button>
              <button
                onClick={() => void runOptimize()}
                disabled={!store.canPreviewOptimization || optimizePending}
              >
                {optimizePending ? 'Optimizing...' : 'Preview Optimization'}
              </button>
            </div>
            {store.optimizePanelEntries.length > 0 ? (
              <div className="optimize-panel-log" role="status" aria-live="polite">
                {store.optimizePanelEntries.map((entry, i) => (
                  <div
                    key={`${i}-${entry.line.slice(0, 48)}`}
                    className={`optimize-panel-log__line optimize-panel-log__line--${entry.level}`}
                  >
                    {entry.line}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        }
        middle={<PipelineGraphPanel ir={store.analysis?.ir ?? null} issues={store.analysis?.issues ?? []} />}
        right={
          <OptimizationAssistantPanel
            issues={store.analysis?.issues ?? []}
            explanation={store.optimization?.explanation}
            llmUsed={store.optimization?.llm_used}
            fileName={store.fileName}
            currentCode={store.currentCode}
            onApplyCode={(code) => {
              store.setCurrentCode(code)
              store.setOptimization(null)
              store.setAnalysis(null)
            }}
          />
        }
        bottom={
          <MetricsBar
            before={store.optimization?.metrics_before ?? store.analysis?.metrics_before}
            after={store.optimization?.metrics_after}
          />
        }
      />

      <DiffPreviewModal
        isOpen={store.showDiff}
        originalCode={store.currentCode}
        optimizedCode={store.optimization?.optimized_code ?? store.currentCode}
        onAccept={() => {
          if (store.optimization?.optimized_code) {
            store.setCurrentCode(store.optimization.optimized_code)
          }
          store.setShowDiff(false)
        }}
        onReject={() => store.setShowDiff(false)}
      />
    </>
  )
}
