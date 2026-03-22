import { useMutation } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'

import { chatWithAssistant } from '../../lib/api/client'
import { renderSimpleMarkdown } from '../../lib/markdown/renderSimpleMarkdown'
import type { ChatMessage, Issue } from '../../lib/api/types'

const SEVERITY_ORDER: Record<Issue['severity'], number> = { high: 0, medium: 1, low: 2 }

type GroupedIssue = {
  issue_type: string
  title: string
  severity: Issue['severity']
  count: number
  suggested_action: string
}

function groupIssuesByType(issues: Issue[]): GroupedIssue[] {
  const byType = new Map<string, Issue[]>()
  for (const issue of issues) {
    const list = byType.get(issue.issue_type)
    if (list) list.push(issue)
    else byType.set(issue.issue_type, [issue])
  }
  return [...byType.values()]
    .map((list) => ({
      issue_type: list[0].issue_type,
      title: list[0].title,
      severity: list[0].severity,
      count: list.length,
      suggested_action: list[0].suggested_action,
    }))
    .sort(
      (a, b) =>
        SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] || b.count - a.count,
    )
}

function formatApiError(err: unknown): string {
  if (typeof err === 'object' && err !== null && 'response' in err) {
    const r = (err as { response?: { data?: { detail?: unknown } } }).response
    const d = r?.data?.detail
    if (typeof d === 'string') return d
    if (Array.isArray(d)) return d.map((x) => JSON.stringify(x)).join(', ')
  }
  if (err instanceof Error) return err.message
  return 'Request failed'
}

type Props = {
  issues: Issue[]
  explanation?: string
  llmUsed?: boolean
  fileName: string
  currentCode: string
  onApplyCode: (code: string) => void
}

export function OptimizationAssistantPanel({
  issues,
  explanation,
  llmUsed,
  fileName,
  currentCode,
  onApplyCode,
}: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [pendingCode, setPendingCode] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const chat = useMutation({
    mutationFn: chatWithAssistant,
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: 'assistant', content: data.assistant_message }])
      if (data.updated_code) {
        setPendingCode(data.updated_code)
      }
    },
  })

  const canSend = useMemo(() => draft.trim().length > 0 && !chat.isPending, [draft, chat.isPending])

  const groupedIssues = useMemo(() => groupIssuesByType(issues), [issues])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, chat.isPending])

  const send = () => {
    if (!canSend) return
    const userMsg: ChatMessage = { role: 'user', content: draft.trim() }
    const next = [...messages, userMsg]
    setMessages(next)
    setDraft('')
    chat.mutate({
      file_name: fileName,
      current_code: currentCode,
      messages: next,
    })
  }

  return (
    <div className="stack assistant-panel">
      <h2>Optimization Assistant</h2>
      <div>
        <h3>Detected Issues</h3>
        {groupedIssues.length === 0 ? (
          <p className="hint">No issues detected yet.</p>
        ) : (
          <ul className="issues issues--grouped">
            {groupedIssues.map((g) => (
              <li key={g.issue_type}>
                <div className="issues__row">
                  <strong>{g.title}</strong>
                  <span className="issues__count" title="How many times this pattern was detected">
                    {g.count} {g.count === 1 ? 'occurrence' : 'occurrences'}
                  </span>
                </div>
                <p className="hint issues__suggestion">Suggestion: {g.suggested_action}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <h3>Suggested Optimization</h3>
        {llmUsed !== undefined && (
          <p className="hint">
            {llmUsed ? 'Last preview used OpenRouter (LLM).' : 'Last preview used local deterministic rewrite (set OPENROUTER_API_KEY in backend/.env for LLM).'}
          </p>
        )}
        {explanation?.trim() ? (
          <div className="markdown-explanation optimization-explanation">{renderSimpleMarkdown(explanation)}</div>
        ) : (
          <p className="hint">Preview optimization to view generated suggestion.</p>
        )}
      </div>

      <div className="chat-section">
        <h3>Chat with agent</h3>
        <p className="hint">
          Uses the same OpenRouter model as optimization. Ask for edits to the current file; if the model returns a{' '}
          <code>python</code> block, you can apply it to the editor.
        </p>
        <div className="chat-log">
          {messages.length === 0 && <p className="hint">No messages yet.</p>}
          {messages.map((m, i) => (
            <div key={`${i}-${m.role}`} className={m.role === 'user' ? 'chat-msg user' : 'chat-msg assistant'}>
              <strong>{m.role === 'user' ? 'You' : 'Assistant'}</strong>
              <pre className="chat-bubble">{m.content}</pre>
            </div>
          ))}
          {chat.isPending && <p className="hint">Thinking…</p>}
          {chat.isError && <p className="chat-error">{formatApiError(chat.error)}</p>}
          <div ref={bottomRef} />
        </div>
        {pendingCode && (
          <div className="pending-code">
            <p className="hint">The assistant proposed new code.</p>
            <div className="actions">
              <button type="button" onClick={() => setPendingCode(null)}>
                Dismiss
              </button>
              <button
                type="button"
                onClick={() => {
                  onApplyCode(pendingCode)
                  setPendingCode(null)
                }}
              >
                Apply to editor
              </button>
            </div>
          </div>
        )}
        <div className="chat-input-row">
          <textarea
            className="chat-input"
            rows={3}
            placeholder="e.g. Merge the two invoke calls into one prompt…"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
          />
          <button type="button" disabled={!canSend} onClick={send}>
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
