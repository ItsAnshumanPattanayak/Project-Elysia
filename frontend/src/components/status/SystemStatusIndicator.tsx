import { useSystemStatus } from '../../hooks/useSystemStatus'

export function SystemStatusIndicator() {
  const { health, ai, error, loading, refresh } = useSystemStatus()
  const aiLabel =
    ai?.state === 'ready'
      ? 'Model ready · generation may be slow'
      : ai?.state === 'model_not_configured'
        ? 'Model not configured'
        : ai?.state === 'model_not_installed'
          ? 'Configured model missing'
          : 'Ollama unavailable'
  return (
    <details className="system-status">
      <summary aria-label="Local system status">
        <span className={`status-dot ${error ? 'bad' : 'good'}`} />
        <span>
          {loading ? 'Checking local services' : error || 'Local services'}
        </span>
      </summary>
      <div className="status-details">
        <p>
          <strong>Backend</strong>
          <span>{health ? 'Connected' : 'Unavailable'}</span>
        </p>
        <p>
          <strong>Database</strong>
          <span>{health?.database ?? 'Unknown'}</span>
        </p>
        <p>
          <strong>Ollama</strong>
          <span>{aiLabel}</span>
        </p>
        <p>
          <strong>Model</strong>
          <span>{ai?.configured_model ?? 'None selected'}</span>
        </p>
        <button
          type="button"
          className="text-button"
          onClick={() => void refresh()}
        >
          Refresh status
        </button>
      </div>
    </details>
  )
}
