import { describe, expect, it } from 'vitest'
import { chatReducer, initialStreamState } from './chatReducer'

const message = {
  id: 1,
  conversation_id: 1,
  sender: 'user' as const,
  raw_content: 'Hi',
  narration: null,
  dialogue: null,
  emotion: null,
  message_metadata: {},
  sequence_number: 1,
  is_edited: false,
  created_at: 'x',
  edited_at: null,
}
describe('stream state machine', () => {
  it('starts deterministically', () => {
    expect(
      chatReducer(initialStreamState, {
        type: 'submit',
        conversationId: 2,
        content: 'Hello',
      }),
    ).toMatchObject({
      phase: 'submitting',
      conversationId: 2,
      retryContent: 'Hello',
    })
  })
  it('moves through accepted and user reconciliation', () => {
    const submitted = chatReducer(initialStreamState, {
      type: 'submit',
      conversationId: 1,
      content: 'Hi',
    })
    expect(chatReducer(submitted, { type: 'accepted' }).phase).toBe('accepted')
    expect(
      chatReducer(submitted, { type: 'user', message }).persistedUser,
    ).toEqual(message)
  })
  it('appends tokens in exact order', () => {
    let state = chatReducer(initialStreamState, {
      type: 'submit',
      conversationId: 1,
      content: 'Hi',
    })
    state = chatReducer(state, { type: 'token', text: 'Tum ' })
    state = chatReducer(state, { type: 'token', text: 'theek?' })
    expect(state.text).toBe('Tum theek?')
  })
  it('merges metadata', () => {
    let state = chatReducer(initialStreamState, {
      type: 'metadata',
      data: { a: 1 },
    })
    state = chatReducer(state, { type: 'metadata', data: { b: 2 } })
    expect(state.metadata).toEqual({ a: 1, b: 2 })
  })
  it('enters completing then completed and clears text', () => {
    let state = { ...initialStreamState, text: 'partial' }
    state = chatReducer(state, { type: 'completing' })
    expect(state.phase).toBe('completing')
    state = chatReducer(state, { type: 'complete' })
    expect(state).toMatchObject({ phase: 'completed', text: '' })
  })
  it('failure keeps retry content and clears partial output', () => {
    const state = chatReducer(
      { ...initialStreamState, text: 'partial', retryContent: 'Hi' },
      { type: 'fail', message: 'Timeout' },
    )
    expect(state).toMatchObject({
      phase: 'failed',
      text: '',
      retryContent: 'Hi',
      error: 'Timeout',
    })
  })
  it('cancellation clears partial output', () => {
    expect(
      chatReducer(
        { ...initialStreamState, text: 'partial' },
        { type: 'cancel' },
      ),
    ).toMatchObject({ phase: 'cancelled', text: '' })
  })
  it('reset removes stale conversation state', () => {
    expect(
      chatReducer(
        { ...initialStreamState, phase: 'generating', conversationId: 5 },
        { type: 'reset' },
      ),
    ).toEqual(initialStreamState)
  })
})
