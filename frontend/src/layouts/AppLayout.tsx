import type { ReactNode } from 'react'

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="shell">
      <header>
        <a href="/" className="brand">
          <span className="mark">E</span>
          <span>Project Elysia</span>
        </a>
        <span className="batch">Character engine · Batch 2</span>
      </header>
      {children}
      <footer>
        <span>Runs on your machine</span>
        <span>Private by design · No telemetry</span>
      </footer>
    </div>
  )
}
