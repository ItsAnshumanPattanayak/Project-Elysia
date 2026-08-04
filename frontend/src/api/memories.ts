import type { MemoryList } from '../types/memory'
import { requestJson } from './client'
import { isMemoryList } from './guards'

export const listMemories = (
  conversationId: number,
  options: { status?: string; limit?: number } = {},
  signal?: AbortSignal,
) => {
  const query = new URLSearchParams({
    status: options.status ?? 'active',
    limit: String(options.limit ?? 1),
  })
  return requestJson<MemoryList>(
    `/api/conversations/${conversationId}/memories?${query}`,
    isMemoryList,
    { signal },
  )
}
