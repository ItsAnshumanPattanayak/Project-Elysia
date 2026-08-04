import type {
  ManualMemoryCreate,
  MemoryDetail,
  MemoryList,
  MemoryRebuild,
  MemorySearchPreview,
  MemoryType,
  MemoryUpdate,
} from '../types/memory'
import { isObject, requestJson, requestVoid } from './client'
import { isMemoryList } from './guards'

export const listMemories = (
  conversationId: number,
  options: {
    status?: string
    type?: string
    source?: string
    pinned?: boolean
    locked?: boolean
    sensitive?: boolean
    query?: string
    offset?: number
    limit?: number
  } = {},
  signal?: AbortSignal,
) => {
  const query = new URLSearchParams({
    limit: String(options.limit ?? 1),
    offset: String(options.offset ?? 0),
  })
  if (options.status !== '') query.set('status', options.status ?? 'active')
  if (options.type) query.set('memory_type', options.type)
  if (options.source) query.set('source', options.source)
  if (options.pinned !== undefined) query.set('pinned', String(options.pinned))
  if (options.locked !== undefined) query.set('locked', String(options.locked))
  if (options.sensitive !== undefined)
    query.set('sensitive', String(options.sensitive))
  if (options.query) query.set('query', options.query)
  return requestJson<MemoryList>(
    `/api/conversations/${conversationId}/memories?${query}`,
    isMemoryList,
    { signal },
  )
}

const isMemory = (value: unknown): value is MemoryDetail =>
  isObject(value) &&
  typeof value.id === 'number' &&
  typeof value.content === 'string'
const isPreview = (value: unknown): value is MemorySearchPreview =>
  isObject(value) && Array.isArray(value.items)
const isRebuild = (value: unknown): value is MemoryRebuild =>
  isObject(value) && isObject(value.before) && isObject(value.after)

export const getMemory = (
  conversationId: number,
  memoryId: number,
  signal?: AbortSignal,
) =>
  requestJson<MemoryDetail>(
    `/api/conversations/${conversationId}/memories/${memoryId}`,
    isMemory,
    { signal },
  )
export const createMemory = (
  conversationId: number,
  payload: ManualMemoryCreate,
  signal?: AbortSignal,
) =>
  requestJson<MemoryDetail>(
    `/api/conversations/${conversationId}/memories`,
    isMemory,
    { method: 'POST', body: JSON.stringify(payload), signal },
  )
export const updateMemory = (
  conversationId: number,
  memoryId: number,
  payload: MemoryUpdate,
  signal?: AbortSignal,
) =>
  requestJson<MemoryDetail>(
    `/api/conversations/${conversationId}/memories/${memoryId}`,
    isMemory,
    { method: 'PATCH', body: JSON.stringify(payload), signal },
  )
export const archiveMemory = (
  conversationId: number,
  memoryId: number,
  signal?: AbortSignal,
) =>
  requestVoid(`/api/conversations/${conversationId}/memories/${memoryId}`, {
    method: 'DELETE',
    signal,
  })
export const searchMemoryPreview = (
  conversationId: number,
  payload: { query: string; memory_types?: MemoryType[]; limit?: number },
  signal?: AbortSignal,
) =>
  requestJson<MemorySearchPreview>(
    `/api/conversations/${conversationId}/memories/search-preview`,
    isPreview,
    { method: 'POST', body: JSON.stringify(payload), signal },
  )
export const rebuildMemories = (conversationId: number, signal?: AbortSignal) =>
  requestJson<MemoryRebuild>(
    `/api/conversations/${conversationId}/memories/rebuild`,
    isRebuild,
    { method: 'POST', body: JSON.stringify({ confirm: true }), signal },
  )
