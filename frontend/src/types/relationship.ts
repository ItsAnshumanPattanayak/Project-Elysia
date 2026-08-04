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
}
