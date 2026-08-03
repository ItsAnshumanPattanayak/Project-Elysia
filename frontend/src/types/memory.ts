export type MemoryType =
  | 'user_fact'
  | 'user_preference'
  | 'user_dislike'
  | 'user_goal'
  | 'user_habit'
  | 'user_boundary'
  | 'user_relationship_fact'
  | 'shared_experience'
  | 'promise'
  | 'commitment'
  | 'conflict'
  | 'reconciliation'
  | 'emotional_moment'
  | 'character_fact'
  | 'scene_fact'
  | 'story_fact'
  | 'important_quote'
  | 'recurring_topic'
  | 'private_note'

export type MemoryStatus = 'active' | 'archived' | 'superseded' | 'reverted'
export type MemorySource =
  | 'model_candidate'
  | 'deterministic_user_fact'
  | 'manual'
  | 'consolidation'
  | 'system_rebuild'

export interface Memory {
  id: number
  conversation_id: number
  content: string
  memory_type: MemoryType
  importance: number
  confidence: number
  tags: string[]
  source: MemorySource
  status: MemoryStatus
  is_sensitive: boolean
  is_pinned: boolean
  is_locked: boolean
  usage_count: number
  created_at: string
  updated_at: string
}

export interface MemoryList {
  items: Memory[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface ManualMemoryCreate {
  content: string
  memory_type: MemoryType
  importance?: number
  tags?: string[]
  sensitive?: boolean
  confirm_sensitive?: boolean
  pinned?: boolean
  locked?: boolean
  note?: string
}

export interface MemoryUpdate extends Partial<ManualMemoryCreate> {
  archived?: boolean
  force?: boolean
  reason?: string
}
