import { useMemo, useState } from 'react'
import type { AnalyzeResponse, OptimizeResponse } from '../api/types'

const DEFAULT_SAMPLE = `"""
Default demo pipeline for the LLM Pipeline Optimizer UI.

This is a LangChain-style script with several ChatOpenAI "agents" (one model instance
per role). The flow is intentionally verbose so the analyzer can surface mergeable
steps, repeated routing, and duplicate invoke labels.
"""

from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI

# ---------------------------------------------------------------------------
# Agent roster — each ChatOpenAI instance represents a distinct role/persona.
# Only .invoke(...) counts as an LLM call in the IR; constructors do not.
# ---------------------------------------------------------------------------

# Plans the workflow from raw user input (ticket, feature request, etc.).
planner = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

# Gathers facts; invoked twice to mimic "search then refine" without a real retriever.
researcher = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

# Produces a first draft from the research notes.
writer = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)

# Reviews draft for quality and safety.
critic = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

# Checks claims against the original input (lightweight "grounding" pass).
fact_checker = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

# Compresses the validated answer for downstream steps.
summarizer = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

# Turns structured output into user-facing Markdown.
formatter = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

# Decides next action and merges branches; invoked twice (route + finalize).
router = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

# Shared instructions prepended to several steps — mirrors "repeated system context"
# patterns that the optimizer may flag for deduplication.
SHARED_SYSTEM = (
    "You are part of a multi-agent support pipeline. "
    "Be concise, cite uncertainty, and never invent ticket IDs."
)

# ---------------------------------------------------------------------------
# Prompt templates (LangChain) — kept separate so the graph shows prompt nodes.
# ---------------------------------------------------------------------------

plan_prompt = PromptTemplate.from_template(
    SHARED_SYSTEM
    + "\\n\\nBreak this user request into 3–5 concrete sub-tasks:\\n\\n{user_input}"
)

research_prompt_a = PromptTemplate.from_template(
    SHARED_SYSTEM + "\\n\\nList unknowns and search queries for:\\n\\n{plan}"
)

research_prompt_b = PromptTemplate.from_template(
    SHARED_SYSTEM + "\\n\\nRefine the queries given partial notes:\\n\\n{notes}"
)

draft_prompt = PromptTemplate.from_template(
    "Write a short draft answer using:\\nPlan:\\n{plan}\\nNotes:\\n{notes}"
)

critique_prompt = PromptTemplate.from_template(
    "List issues and risks in this draft:\\n\\n{draft}"
)

ground_prompt = PromptTemplate.from_template(
    "Which statements are unsupported by the ticket text?\\n\\nTicket:\\n{ticket}\\n\\nDraft:\\n{draft}"
)

summary_prompt = PromptTemplate.from_template(
    "Summarize the critique and grounding in 5 bullets:\\n\\n{critique}\\n\\n{grounding}"
)

format_prompt = PromptTemplate.from_template(
    "Format as Markdown with ## headings:\\n\\n{summary}"
)

route_prompt_a = PromptTemplate.from_template(
    "Choose branch: expand | finalize | escalate. Context:\\n\\n{context}"
)

route_prompt_b = PromptTemplate.from_template(
    "Produce the final user-visible message from:\\n\\n{context}"
)

# ---------------------------------------------------------------------------
# Pipeline — data flows downstream; researcher and router run more than once.
# ---------------------------------------------------------------------------

plan = planner.invoke(plan_prompt.format(user_input=user_input))

raw_notes = researcher.invoke(research_prompt_a.format(plan=plan))
refined_notes = researcher.invoke(research_prompt_b.format(notes=raw_notes))

draft = writer.invoke(draft_prompt.format(plan=plan, notes=refined_notes))
critique = critic.invoke(critique_prompt.format(draft=draft))
grounding = fact_checker.invoke(ground_prompt.format(ticket=user_input, draft=draft))

brief = summarizer.invoke(summary_prompt.format(critique=critique, grounding=grounding))
markdown = formatter.invoke(format_prompt.format(summary=brief))

route_context = SHARED_SYSTEM + "\\n\\n" + str(markdown)
branch = router.invoke(route_prompt_a.format(context=route_context))
final_reply = router.invoke(
    route_prompt_b.format(context=str(markdown) + "\\n\\n" + str(branch))
)

print(final_reply)
`

export function usePipelineStore() {
  const [fileName, setFileName] = useState('pipeline.py')
  const [originalCode, setOriginalCode] = useState(DEFAULT_SAMPLE)
  const [currentCode, setCurrentCode] = useState(DEFAULT_SAMPLE)
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null)
  const [optimization, setOptimization] = useState<OptimizeResponse | null>(null)
  const [showDiff, setShowDiff] = useState(false)
  const [optimizePanelLog, setOptimizePanelLog] = useState<string[]>([])

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
    optimizePanelLog,
    setOptimizePanelLog,
  }
}
