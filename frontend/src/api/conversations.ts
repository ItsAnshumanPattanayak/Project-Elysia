import type {
  CharacterSummary,
  ConversationCreate,
  ConversationDetail,
  ConversationList,
  ConversationUpdate,
} from '../types/conversation'
import { isObject, requestJson, requestVoid } from './client'
import { isConversation, isConversationList } from './guards'

export const listConversations = (
  options: { offset?: number; limit?: number; archived?: boolean } = {},
  signal?: AbortSignal,
) => {
  const query = new URLSearchParams()
  if (options.offset) query.set('offset', String(options.offset))
  if (options.limit) query.set('limit', String(options.limit))
  if (options.archived !== undefined)
    query.set('archived', String(options.archived))
  return requestJson<ConversationList>(
    `/api/conversations?${query}`,
    isConversationList,
    { signal },
  )
}
export const getConversation = (id: number, signal?: AbortSignal) =>
  requestJson<ConversationDetail>(`/api/conversations/${id}`, isConversation, {
    signal,
  })
export const createConversation = (payload: ConversationCreate) =>
  requestJson<ConversationDetail>('/api/conversations', isConversation, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
export const updateConversation = (id: number, payload: ConversationUpdate) =>
  requestJson<ConversationDetail>(`/api/conversations/${id}`, isConversation, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
export const deleteConversation = (id: number) =>
  requestVoid(`/api/conversations/${id}`, { method: 'DELETE' })

const isCharacter = (v: unknown): v is CharacterSummary =>
  isObject(v) &&
  typeof v.slug === 'string' &&
  typeof v.display_name === 'string' &&
  typeof v.description === 'string'
export const listCharacters = (signal?: AbortSignal) =>
  requestJson<CharacterSummary[]>(
    '/api/characters',
    (v): v is CharacterSummary[] => Array.isArray(v) && v.every(isCharacter),
    { signal },
  )
export const getCharacter = (slug: string, signal?: AbortSignal) =>
  requestJson<CharacterSummary>(`/api/characters/${slug}`, isCharacter, {
    signal,
  })
