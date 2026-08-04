import { useCallback, useEffect, useState } from 'react'
import { getAIStatus, getHealth } from '../api/system'
import type { AIStatus, HealthStatus } from '../types/system'
import { LoadingScreen } from './LoadingScreen'

const unavailableStatus: AIStatus = {
  provider: 'ollama',
  available: false,
  state: 'unavailable',
  version: null,
  configured_model: null,
  model_ready: false,
  base_url: 'local',
  error_code: 'ollama_unavailable',
  message: 'AI status could not be reached.',
}

export function AppStatus() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [ai, setAI] = useState<AIStatus | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async (refreshAI = false) => {
    setLoading(true)
    setError('')
    try {
      setHealth(await getHealth())
      try {
        setAI(await getAIStatus(refreshAI))
      } catch {
        setAI(unavailableStatus)
      }
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'Backend is unavailable',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(false)
  }, [load])
  if (loading) return <LoadingScreen />
  if (error)
    return (
      <div className="status error" role="alert">
        <span>
          <strong>Backend unavailable</strong>
          <small>{error}</small>
        </span>
        <button type="button" onClick={() => void load(false)}>
          Retry connection
        </button>
      </div>
    )

  const aiLabel = {
    ready: 'Ollama ready',
    unavailable: 'Ollama unavailable',
    model_not_configured: 'Model not configured',
    model_not_installed: 'Configured model missing',
  }[ai?.state ?? 'unavailable']
  return (
    <div className="status-stack" role="status">
      <div className="status success">
        <span className="pulse" />
        <span>
          <strong>Backend connected</strong>
          <small>
            {health?.environment} · API {health?.version}
          </small>
        </span>
        <span className="database">Database: {health?.database}</span>
      </div>
      <div className={`status ai-status ${ai?.state ?? 'unavailable'}`}>
        <span className="pulse" />
        <span>
          <strong>{aiLabel}</strong>
          <small>{ai?.message}</small>
          <small>
            Version {ai?.version ?? 'unknown'} · Model{' '}
            {ai?.configured_model ?? 'not configured'}
          </small>
        </span>
        <button type="button" onClick={() => void load(true)}>
          Refresh AI status
        </button>
      </div>
    </div>
  )
}
