export interface RelationshipState {
  conversation_id: number
  attraction: number
  trust: number
  affection: number
  respect: number
  comfort: number
  jealousy: number
  anger: number
  mood: string
  relationship_stage: string
  turn_count: number
  locked_values: Record<string, boolean>
  baseline_values: Record<string, unknown>
  updated_at: string
}

export interface RelationshipEvent {
  id: number
  conversation_id: number
  source_user_message_id: number | null
  source_character_message_id: number | null
  event_type: string
  source: string
  confidence: number
  evidence: Array<{ kind?: string; description?: string }>
  score_deltas: Record<string, number>
  values_before: Record<string, unknown>
  values_after: Record<string, unknown>
  mood_before: string
  mood_after: string
  stage_before: string
  stage_after: string
  is_reverted: boolean
  reverted_at: string | null
  created_at: string
}

export interface RelationshipEventList {
  items: RelationshipEvent[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface RelationshipUpdate {
  attraction?: number
  trust?: number
  affection?: number
  respect?: number
  comfort?: number
  jealousy?: number
  anger?: number
  mood?: string
  relationship_stage?: string
  locked_values?: Record<string, boolean>
  force?: boolean
  reason: string
}

export interface RelationshipMutation {
  event_id: number
  suppressed_by_locks: string[]
  values_before: Record<string, number>
  values_after: Record<string, number>
}

export interface RelationshipRecalculation {
  before: RelationshipState
  after: RelationshipState
  warnings: string[]
}
