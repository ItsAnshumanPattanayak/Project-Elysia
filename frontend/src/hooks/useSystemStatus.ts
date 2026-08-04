import { useCallback, useEffect, useState } from 'react'
import { getAIStatus, getHealth } from '../api/system'
import type { AIStatus, HealthStatus } from '../types/system'

export function useSystemStatus() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [ai, setAI] = useState<AIStatus | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const load = useCallback(async (refresh = false) => {
    const controller = new AbortController()
    setLoading(true)
    try {
      setHealth(await getHealth(controller.signal))
      setError('')
      try {
        setAI(await getAIStatus(refresh, controller.signal))
      } catch {
        setAI(null)
      }
    } catch {
      setError('The local backend is unavailable.')
    } finally {
      setLoading(false)
    }
    return () => controller.abort()
  }, [])
  useEffect(() => {
    void load()
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void load()
    }, 30_000)
    return () => window.clearInterval(timer)
  }, [load])
  return { health, ai, error, loading, refresh: () => load(true) }
}
