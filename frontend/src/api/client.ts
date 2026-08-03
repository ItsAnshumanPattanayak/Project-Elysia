import { API_BASE_URL } from '../config/env'
import type {
  AIStatus,
  HealthStatus,
  RootStatus,
  SystemInfo,
} from '../types/system'
import type {
  ManualMemoryCreate,
  Memory,
  MemoryList,
  MemoryUpdate,
} from '../types/memory'

export class ApiError extends Error {}

async function request<T>(
  path: string,
  validate: (value: unknown) => value is T,
  init?: RequestInit,
): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 5000)
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
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
  typeof value.ai_integration === 'string' &&
  isObject(value.documentation)
const isAIStatus = (value: unknown): value is AIStatus =>
  isObject(value) &&
  value.provider === 'ollama' &&
  typeof value.available === 'boolean' &&
  typeof value.state === 'string' &&
  typeof value.model_ready === 'boolean' &&
  typeof value.base_url === 'string' &&
  typeof value.message === 'string'
const isMemory = (value: unknown): value is Memory =>
  isObject(value) &&
  typeof value.id === 'number' &&
  typeof value.conversation_id === 'number' &&
  typeof value.content === 'string' &&
  typeof value.memory_type === 'string' &&
  typeof value.importance === 'number' &&
  typeof value.confidence === 'number' &&
  Array.isArray(value.tags) &&
  typeof value.status === 'string'
const isMemoryList = (value: unknown): value is MemoryList =>
  isObject(value) &&
  Array.isArray(value.items) &&
  value.items.every(isMemory) &&
  typeof value.total === 'number' &&
  typeof value.limit === 'number' &&
  typeof value.offset === 'number' &&
  typeof value.has_more === 'boolean'

export const api = {
  root: () => request('/', isRoot),
  health: () => request('/health', isHealth),
  systemInfo: () => request('/api/system/info', isSystem),
  aiStatus: (refresh = false) =>
    request(`/api/ai/status${refresh ? '?refresh=true' : ''}`, isAIStatus),
  memories: (conversationId: number) =>
    request(`/api/conversations/${conversationId}/memories`, isMemoryList),
  createMemory: (conversationId: number, payload: ManualMemoryCreate) =>
    request(`/api/conversations/${conversationId}/memories`, isMemory, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateMemory: (
    conversationId: number,
    memoryId: number,
    payload: MemoryUpdate,
  ) =>
    request(
      `/api/conversations/${conversationId}/memories/${memoryId}`,
      isMemory,
      { method: 'PATCH', body: JSON.stringify(payload) },
    ),
}
