import type { AIModel, AIStatus, HealthStatus } from '../types/system'
import { isObject, requestJson } from './client'
import { isAIStatus, isHealth } from './guards'

export const getHealth = (signal?: AbortSignal) =>
  requestJson<HealthStatus>('/health', isHealth, { signal })
export const getAIStatus = (refresh = false, signal?: AbortSignal) =>
  requestJson<AIStatus>(
    `/api/ai/status${refresh ? '?refresh=true' : ''}`,
    isAIStatus,
    { signal },
  )
const isModels = (value: unknown): value is AIModel[] =>
  Array.isArray(value) &&
  value.every((item) => isObject(item) && typeof item.name === 'string')
export const listModels = (refresh = false, signal?: AbortSignal) =>
  requestJson<AIModel[]>(
    `/api/ai/models${refresh ? '?refresh=true' : ''}`,
    isModels,
    { signal },
  )
