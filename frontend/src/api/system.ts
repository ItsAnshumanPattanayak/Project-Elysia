import type { AIStatus, HealthStatus } from '../types/system'
import { requestJson } from './client'
import { isAIStatus, isHealth } from './guards'

export const getHealth = (signal?: AbortSignal) =>
  requestJson<HealthStatus>('/health', isHealth, { signal })
export const getAIStatus = (refresh = false, signal?: AbortSignal) =>
  requestJson<AIStatus>(
    `/api/ai/status${refresh ? '?refresh=true' : ''}`,
    isAIStatus,
    { signal },
  )
