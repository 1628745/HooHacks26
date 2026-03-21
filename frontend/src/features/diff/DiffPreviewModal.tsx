import { diffLines } from 'diff'

type Props = {
  isOpen: boolean
  originalCode: string
  optimizedCode: string
  onAccept: () => void
  onReject: () => void
}

export function DiffPreviewModal({ isOpen, originalCode, optimizedCode, onAccept, onReject }: Props) {
  if (!isOpen) {
    return null
  }
  const chunks = diffLines(originalCode, optimizedCode)

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <h2>Preview Optimization Diff</h2>
        <div className="diff-wrap">
          {chunks.map((chunk, idx) => (
            <pre
              key={`${idx}-${chunk.added ? 'a' : chunk.removed ? 'r' : 'u'}`}
              className={chunk.added ? 'diff-add' : chunk.removed ? 'diff-remove' : 'diff-keep'}
            >
              {chunk.value}
            </pre>
          ))}
        </div>
        <div className="actions">
          <button onClick={onReject}>Reject</button>
          <button onClick={onAccept}>Accept Optimization</button>
        </div>
      </div>
    </div>
  )
}
