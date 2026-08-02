import { API_BASE_URL } from '../config/env'
import type { HealthStatus, RootStatus, SystemInfo } from '../types/system'

export class ApiError extends Error {}

async function request<T>(
  path: string,
  validate: (value: unknown) => value is T,
): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 5000)
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      signal: controller.signal,
    })
    if (!response.ok) throw new ApiError(`Backend returned ${response.status}`)
    const payload: unknown = await response.json()
    if (!validate(payload))
      throw new ApiError('Backend returned an invalid response')
    return payload
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError(
      error instanceof Error && error.name === 'AbortError'
        ? 'Backend request timed out'
        : 'Backend is unavailable',
    )
  } finally {
    window.clearTimeout(timeout)
  }
}

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null
const isRoot = (value: unknown): value is RootStatus =>
  isObject(value) &&
  typeof value.name === 'string' &&
  typeof value.version === 'string' &&
  value.status === 'running'
const isHealth = (value: unknown): value is HealthStatus =>
  isObject(value) &&
  value.status === 'healthy' &&
  value.database === 'connected' &&
  typeof value.application === 'string' &&
  typeof value.version === 'string' &&
  typeof value.environment === 'string'
const isSystem = (value: unknown): value is SystemInfo =>
  isObject(value) &&
  typeof value.application === 'string' &&
  typeof value.version === 'string' &&
  typeof value.environment === 'string' &&
  typeof value.database_type === 'string' &&
  typeof value.local_first === 'boolean' &&
  value.ai_integration === 'not_configured' &&
  isObject(value.documentation)

export const api = {
  root: () => request('/', isRoot),
  health: () => request('/health', isHealth),
  systemInfo: () => request('/api/system/info', isSystem),
}
