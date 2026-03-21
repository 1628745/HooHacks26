import Editor from '@monaco-editor/react'

type Props = {
  value: string
  onChange: (value: string) => void
}

export function CodeEditorPanel({ value, onChange }: Props) {
  return (
    <div className="stack">
      <h2>Python Source</h2>
      <div className="editor-wrap">
        <Editor
          height="42vh"
          defaultLanguage="python"
          value={value}
          onChange={(next) => onChange(next ?? '')}
          options={{ minimap: { enabled: false }, fontSize: 13 }}
        />
      </div>
    </div>
  )
}
