import { useMemo, useState } from 'react'
import type { AnalyzeResponse, OptimizeResponse } from '../api/types'

const DEFAULT_SAMPLE = `from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI

model = ChatOpenAI(model="gpt-4o-mini")
prompt_a = PromptTemplate.from_template("Summarize this text: {text}")
prompt_b = PromptTemplate.from_template("Format summary as bullets")

step1 = model.invoke(prompt_a.format(text=input_text))
step2 = model.invoke(prompt_b.format(text=step1))
print(step2)
`

export function usePipelineStore() {
  const [fileName, setFileName] = useState('pipeline.py')
  const [originalCode, setOriginalCode] = useState(DEFAULT_SAMPLE)
  const [currentCode, setCurrentCode] = useState(DEFAULT_SAMPLE)
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null)
  const [optimization, setOptimization] = useState<OptimizeResponse | null>(null)
  const [showDiff, setShowDiff] = useState(false)

  const canPreviewOptimization = useMemo(
    () => Boolean(analysis?.ir.nodes.length),
    [analysis?.ir.nodes.length],
  )

  return {
    fileName,
    setFileName,
    originalCode,
    setOriginalCode,
    currentCode,
    setCurrentCode,
    analysis,
    setAnalysis,
    optimization,
    setOptimization,
    showDiff,
    setShowDiff,
    canPreviewOptimization,
  }
}
