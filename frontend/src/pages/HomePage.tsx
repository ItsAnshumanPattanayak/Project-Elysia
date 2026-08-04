import { Redirect } from 'react-router-dom'
import { useApp } from '../state/AppContext'

export function HomePage() {
  const { conversations, loading, error, setNewDialogOpen, refresh } = useApp()
  if (!loading && !error && conversations[0])
    return <Redirect to={`/chat/${conversations[0].id}`} />
  return (
    <main className="welcome-page">
      <div className="welcome-mark">E</div>
      <p className="overline">Local-first · private by design</p>
      <h1>
        Your conversations,
        <br />
        <em>held quietly.</em>
      </h1>
      <p>
        Begin a private character story with Zara. Everything stays on this
        machine, with no telemetry or cloud fallback.
      </p>
      {error ? (
        <div className="welcome-error" role="alert">
          <span>{error}</span>
          <button className="button secondary" onClick={() => void refresh()}>
            Reconnect
          </button>
        </div>
      ) : (
        <button
          className="button welcome-action"
          disabled={loading}
          onClick={() => setNewDialogOpen(true)}
        >
          {loading ? 'Opening your space…' : 'Begin a conversation'}
        </button>
      )}
      <div className="privacy-note">
        <span>◉</span>
        <div>
          <strong>Runs entirely on your machine</strong>
          <small>SQLite history · Local Ollama · No accounts</small>
        </div>
      </div>
    </main>
  )
}
