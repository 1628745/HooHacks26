import type { ReactNode } from 'react'

type Props = {
  left: ReactNode
  middle: ReactNode
  right: ReactNode
}

export function ThreePanelLayout({ left, middle, right }: Props) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <h1>LLM Pipeline Optimizer</h1>
      </header>
      <main className="panels">
        <section className="panel">{left}</section>
        <section className="panel panel--center">{middle}</section>
        <section className="panel">{right}</section>
      </main>
    </div>
  )
}
