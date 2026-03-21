import type { ReactNode } from 'react'

type Props = {
  left: ReactNode
  middle: ReactNode
  right: ReactNode
  bottom: ReactNode
}

export function ThreePanelLayout({ left, middle, right, bottom }: Props) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <h1>LLM Pipeline Optimizer</h1>
      </header>
      <main className="panels">
        <section className="panel">{left}</section>
        <section className="panel">{middle}</section>
        <section className="panel">{right}</section>
      </main>
      <footer className="metrics">{bottom}</footer>
    </div>
  )
}
