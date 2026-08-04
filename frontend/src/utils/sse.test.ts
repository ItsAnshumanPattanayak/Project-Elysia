import { describe, expect, it } from 'vitest'
import { parseSSEFrame, SSEParser } from './sse'

describe('SSE parser', () => {
  it.each([
    ['accepted', { conversation_id: 1 }],
    ['user_message', { id: 2 }],
    ['start', { model: 'test' }],
    ['token', { text: 'Hello' }],
    ['metadata', { warning: null }],
    ['completed', { turn_count: 1 }],
    ['error', { code: 'ollama_timeout' }],
    ['cancelled', { message: 'cancelled' }],
  ])('parses %s event', (name, data) => {
    expect(
      parseSSEFrame(`event: ${name}\ndata: ${JSON.stringify(data)}`),
    ).toEqual({ event: name, data })
  })
  it('parses one complete event', () => {
    expect(
      new SSEParser().push('event: token\ndata: {"text":"A"}\n\n'),
    ).toHaveLength(1)
  })
  it('buffers split frames', () => {
    const parser = new SSEParser()
    expect(parser.push('event: tok')).toEqual([])
    expect(parser.push('en\ndata: {"text":"A"}\n\n')[0].data.text).toBe('A')
  })
  it('parses multiple frames in one chunk in order', () => {
    const result = new SSEParser().push(
      'event: token\ndata: {"text":"A"}\n\nevent: token\ndata: {"text":"B"}\n\n',
    )
    expect(result.map((item) => item.data.text)).toEqual(['A', 'B'])
  })
  it('joins multi-line data', () => {
    expect(
      parseSSEFrame('event: token\ndata: {"text":\ndata: "hello"}'),
    ).toEqual({ event: 'token', data: { text: 'hello' } })
  })
  it('ignores comment heartbeat lines', () => {
    expect(
      parseSSEFrame(': heartbeat\nevent: token\ndata: {"text":"A"}')?.data.text,
    ).toBe('A')
  })
  it('ignores malformed JSON', () => {
    expect(parseSSEFrame('event: token\ndata: nope')).toBeNull()
  })
  it('ignores unknown events', () => {
    expect(parseSSEFrame('event: secret\ndata: {}')).toBeNull()
  })
  it('flushes a final incomplete delimiter frame', () => {
    const parser = new SSEParser()
    parser.push('event: completed\ndata: {"done":true}')
    expect(parser.finish()[0].event).toBe('completed')
  })
  it('preserves UTF-8 characters split as strings', () => {
    const parser = new SSEParser()
    parser.push('event: token\ndata: {"text":"Tum ')
    expect(parser.push('ठीक ho"}\n\n')[0].data.text).toBe('Tum ठीक ho')
  })
  it('handles CRLF', () => {
    expect(
      new SSEParser().push('event: accepted\r\ndata: {}\r\n\r\n')[0].event,
    ).toBe('accepted')
  })
  it('ignores frames without data', () => {
    expect(parseSSEFrame('event: token')).toBeNull()
  })
})
