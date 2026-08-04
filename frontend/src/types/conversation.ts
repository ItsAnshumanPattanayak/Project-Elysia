export interface CharacterReference {
  id: number
  slug: string
  display_name: string
}
export interface RoleplayProfileReference {
  id: number
  roleplay_name: string
}
export interface RelationshipSnapshot {
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
}
export interface ConversationSummary {
  id: number
  title: string
  character: CharacterReference
  roleplay_user: RoleplayProfileReference
  current_scene: string
  relationship_stage: string
  is_active: boolean
  is_archived: boolean
  message_count: number
  turn_count: number
  created_at: string
  updated_at: string
  last_message_at: string | null
}
export interface ConversationDetail extends ConversationSummary {
  relationship_state: RelationshipSnapshot
  recent_messages: Array<{
    id: number
    sender: 'user' | 'character' | 'system'
    raw_content: string
    sequence_number: number
    created_at: string
  }>
}
export interface ConversationList {
  items: ConversationSummary[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}
export interface ConversationCreate {
  character_slug: string
  roleplay_user_slug: string
  title?: string
  current_scene?: string
}
export interface ConversationUpdate {
  title?: string
  current_scene?: string
  is_active?: boolean
  is_archived?: boolean
}
export interface CharacterSummary {
  slug: string
  name: string
  display_name: string
  adult: boolean
  profession: string
  archetype: string
  description: string
}
