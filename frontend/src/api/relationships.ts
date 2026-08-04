import type { RelationshipState } from '../types/relationship'
import { requestJson } from './client'
import { isRelationship } from './guards'

export const getRelationship = (conversationId: number, signal?: AbortSignal) =>
  requestJson<RelationshipState>(
    `/api/conversations/${conversationId}/relationship`,
    isRelationship,
    { signal },
  )
