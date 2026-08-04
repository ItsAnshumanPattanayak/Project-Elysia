export interface MemoryProcessingResult {
  created: number
  consolidated: number
  superseded: number
  rejected: number
  already_applied: number
  memory_ids: number[]
  warnings: string[]
}
export interface Message {
  id: number | string
  conversation_id: number
  sender: 'user' | 'character' | 'system'
  raw_content: string
  narration: string | null
  dialogue: string | null
  emotion: string | null
  message_metadata: Record<string, unknown>
  sequence_number: number
  is_edited: boolean
  created_at: string
  edited_at: string | null
  temporary?: boolean
}
export interface MessageList {
  items: Message[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}
export interface SendMessageRequest {
  content: string
  client_message_id: string
  response_length?: 'concise' | 'balanced' | 'detailed'
  language_mode?: string
}
export interface SendMessageResponse {
  user_message: Message
  character_message: Message
  memory: MemoryProcessingResult | null
  warnings: string[]
}
export interface RegenerateResponse {
  character_message: Message
  turn_count: number
  memory: MemoryProcessingResult | null
  warnings: string[]
}
