import type { Message } from '../types/message'
import type { StreamState } from '../types/streaming'

export const initialStreamState: StreamState = {
  phase: 'idle',
  conversationId: null,
  persistedUser: null,
  text: '',
  metadata: {},
  error: null,
  retryContent: null,
}

export type ChatAction =
  | { type: 'submit'; conversationId: number; content: string }
  | { type: 'accepted' }
  | { type: 'user'; message: Message }
  | { type: 'start' }
  | { type: 'token'; text: string }
  | { type: 'metadata'; data: Record<string, unknown> }
  | { type: 'completing' }
  | { type: 'complete' }
  | { type: 'fail'; message: string }
  | { type: 'cancel' }
  | { type: 'reset' }

export function chatReducer(
  state: StreamState,
  action: ChatAction,
): StreamState {
  switch (action.type) {
    case 'submit':
      return {
        ...initialStreamState,
        phase: 'submitting',
        conversationId: action.conversationId,
        retryContent: action.content,
      }
    case 'accepted':
      return { ...state, phase: 'accepted' }
    case 'user':
      return { ...state, phase: 'accepted', persistedUser: action.message }
    case 'start':
      return { ...state, phase: 'generating' }
    case 'token':
      return { ...state, phase: 'generating', text: state.text + action.text }
    case 'metadata':
      return { ...state, metadata: { ...state.metadata, ...action.data } }
    case 'completing':
      return { ...state, phase: 'completing' }
    case 'complete':
      return { ...state, phase: 'completed', text: '' }
    case 'fail':
      return { ...state, phase: 'failed', text: '', error: action.message }
    case 'cancel':
      return { ...state, phase: 'cancelled', text: '', error: null }
    case 'reset':
      return initialStreamState
  }
}
