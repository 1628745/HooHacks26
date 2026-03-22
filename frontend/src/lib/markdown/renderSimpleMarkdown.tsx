import type { ReactNode } from 'react'

/** Minimal markdown: ## / ### / # headings, **bold**, - bullets, paragraphs. */
export function renderSimpleMarkdown(text: string): ReactNode {
  const blocks = text.split(/\n{2,}/)
  return blocks.map((block, bi) => {
    const lines = block.split('\n')
    const out: ReactNode[] = []
    lines.forEach((line, li) => {
      const t = line.trim()
      if (!t) {
        return
      }
      if (t.startsWith('### ')) {
        out.push(
          <h4 key={`${bi}-${li}-h4`} className="explanation-h4">
            {formatInline(t.slice(4))}
          </h4>,
        )
        return
      }
      if (t.startsWith('## ')) {
        out.push(
          <h3 key={`${bi}-${li}-h3`} className="explanation-h3">
            {formatInline(t.slice(3))}
          </h3>,
        )
        return
      }
      if (t.startsWith('# ')) {
        out.push(
          <h2 key={`${bi}-${li}-h2`} className="explanation-h2">
            {formatInline(t.slice(2))}
          </h2>,
        )
        return
      }
      if (t.startsWith('- ') || t.startsWith('* ')) {
        out.push(
          <div key={`${bi}-${li}-li`} className="explanation-li">
            {formatInline(t.slice(2))}
          </div>,
        )
        return
      }
      out.push(
        <p key={`${bi}-${li}-p`} className="explanation-p">
          {formatInline(t)}
        </p>,
      )
    })
    return (
      <div key={bi} className="explanation-block">
        {out}
      </div>
    )
  })
}

function formatInline(s: string): ReactNode {
  const parts = s.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    return part
  })
}
