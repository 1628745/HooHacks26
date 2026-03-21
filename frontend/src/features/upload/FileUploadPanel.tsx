import type { ChangeEvent } from 'react'

type Props = {
  onLoad: (fileName: string, content: string) => void
}

export function FileUploadPanel({ onLoad }: Props) {
  const onChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }
    const content = await file.text()
    onLoad(file.name, content)
  }

  return (
    <div className="stack">
      <h2>Upload Pipeline</h2>
      <input type="file" accept=".py" onChange={onChange} />
      <p className="hint">Upload a single Python file that contains your LangChain-style pipeline.</p>
    </div>
  )
}
