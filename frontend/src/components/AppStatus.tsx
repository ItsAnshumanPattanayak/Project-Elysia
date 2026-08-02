import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { HealthStatus } from '../types/system'
import { LoadingScreen } from './LoadingScreen'

export function AppStatus() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setHealth(await api.health())
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'Backend is unavailable',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])
  if (loading) return <LoadingScreen />
  if (error)
    return (
      <div className="status error" role="alert">
        <span>
          <strong>Backend unavailable</strong>
          <small>{error}</small>
        </span>
        <button type="button" onClick={() => void load()}>
          Retry connection
        </button>
      </div>
    )
  return (
    <div className="status success" role="status">
      <span className="pulse" />
      <span>
        <strong>Backend connected</strong>
        <small>
          {health?.environment} · API {health?.version}
        </small>
      </span>
      <span className="database">Database: {health?.database}</span>
    </div>
  )
}
