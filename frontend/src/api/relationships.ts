import type {
  RelationshipEventList,
  RelationshipMutation,
  RelationshipRecalculation,
  RelationshipState,
  RelationshipUpdate,
} from '../types/relationship'
import { isObject, requestJson } from './client'
import { isRelationship } from './guards'

export const getRelationship = (conversationId: number, signal?: AbortSignal) =>
  requestJson<RelationshipState>(
    `/api/conversations/${conversationId}/relationship`,
    isRelationship,
    { signal },
  )

const isEventList = (value: unknown): value is RelationshipEventList =>
  isObject(value) &&
  Array.isArray(value.items) &&
  typeof value.total === 'number'
const isMutation = (value: unknown): value is RelationshipMutation =>
  isObject(value) && typeof value.event_id === 'number'
const isRecalculation = (value: unknown): value is RelationshipRecalculation =>
  isObject(value) && isRelationship(value.before) && isRelationship(value.after)

export const listRelationshipEvents = (
  conversationId: number,
  options: {
    limit?: number
    offset?: number
    eventType?: string
    source?: string
    reverted?: boolean
    oldestFirst?: boolean
  } = {},
  signal?: AbortSignal,
) => {
  const query = new URLSearchParams({
    limit: String(options.limit ?? 25),
    offset: String(options.offset ?? 0),
    oldest_first: String(options.oldestFirst ?? false),
  })
  if (options.eventType) query.set('event_type', options.eventType)
  if (options.source) query.set('source', options.source)
  if (options.reverted !== undefined)
    query.set('reverted', String(options.reverted))
  return requestJson<RelationshipEventList>(
    `/api/conversations/${conversationId}/relationship/events?${query}`,
    isEventList,
    { signal },
  )
}

export const updateRelationship = (
  conversationId: number,
  payload: RelationshipUpdate,
  signal?: AbortSignal,
) =>
  requestJson<RelationshipMutation>(
    `/api/conversations/${conversationId}/relationship`,
    isMutation,
    { method: 'PATCH', body: JSON.stringify(payload), signal },
  )

export const recalculateRelationship = (
  conversationId: number,
  signal?: AbortSignal,
) =>
  requestJson<RelationshipRecalculation>(
    `/api/conversations/${conversationId}/relationship/recalculate`,
    isRecalculation,
    { method: 'POST', signal },
  )
