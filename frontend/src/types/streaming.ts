import type { Message } from './message'

export type StreamEventName =
  | 'accepted'
  | 'user_message'
  | 'start'
  | 'token'
  | 'metadata'
  | 'completed'
  | 'error'
  | 'cancelled'

export interface StreamEvent {
  event: StreamEventName
  data: Record<string, unknown>
}
export type StreamPhase =
  | 'idle'
  | 'submitting'
  | 'accepted'
  | 'generating'
  | 'completing'
  | 'completed'
  | 'failed'
  | 'cancelled'
export interface StreamState {
  phase: StreamPhase
  conversationId: number | null
  persistedUser: Message | null
  text: string
  metadata: Record<string, unknown>
  error: string | null
  retryContent: string | null
}
