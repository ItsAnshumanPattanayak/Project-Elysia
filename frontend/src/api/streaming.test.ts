import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { StreamEvent } from '../types/streaming'
import { streamMessage } from './streaming'

const encoder = new TextEncoder()
const streamResponse = (...chunks: string[]) =>
  new Response(
    new ReadableStream({
      start(controller) {
        chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
        controller.close()
      },
    }),
    { headers: { 'Content-Type': 'text/event-stream' } },
  )

describe('streaming client', () => {
  beforeEach(() => vi.restoreAllMocks())
  const payload = { content: 'x', client_message_id: 'client-test' }

  it('posts the message body and dispatches ordered events', async () => {
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(
        streamResponse(
          'event: accepted\ndata: {"request_id":"r1"}\n\n',
          'event: token\ndata: {"text":"Hi"}\n\n',
          'event: completed\ndata: {"message_id":2}\n\n',
        ),
      )
    const events: StreamEvent[] = []
    const controller = new AbortController()
    await streamMessage(
      8,
      { content: 'Hello', client_message_id: 'client-1' },
      (event) => events.push(event),
      controller.signal,
    )
    expect(events.map(({ event }) => event)).toEqual([
      'accepted',
      'token',
      'completed',
    ])
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/conversations/8/messages/stream'),
      expect.objectContaining({
        method: 'POST',
        signal: controller.signal,
        body: JSON.stringify({
          content: 'Hello',
          client_message_id: 'client-1',
        }),
      }),
    )
  })

  it('handles an SSE frame split across byte chunks', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      streamResponse('event: token\nda', 'ta: {"text":"safe"}\n\n'),
    )
    const events: StreamEvent[] = []
    await streamMessage(
      1,
      payload,
      (event) => events.push(event),
      new AbortController().signal,
    )
    expect(events[0]).toMatchObject({ event: 'token', data: { text: 'safe' } })
  })

  it('enforces a bounded streamed output', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      streamResponse('event: token\ndata: {"text":"123456"}\n\n'),
    )
    await expect(
      streamMessage(1, payload, vi.fn(), new AbortController().signal, 5),
    ).rejects.toMatchObject({ code: 'stream_output_limit' })
  })

  it('rejects a response without a readable body', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null))
    await expect(
      streamMessage(1, payload, vi.fn(), new AbortController().signal),
    ).rejects.toMatchObject({ code: 'stream_unsupported' })
  })

  it('normalizes pre-stream HTTP errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: 'conversation_busy',
            message: 'Busy',
            retryable: true,
          },
        }),
        { status: 409, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    await expect(
      streamMessage(1, payload, vi.fn(), new AbortController().signal),
    ).rejects.toMatchObject({ code: 'conversation_busy', status: 409 })
  })

  it('normalizes connection failures', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'))
    await expect(
      streamMessage(1, payload, vi.fn(), new AbortController().signal),
    ).rejects.toMatchObject({ code: 'network_error', retryable: true })
  })

  it('preserves AbortError for cancellation handling', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(
      new DOMException('cancelled', 'AbortError'),
    )
    await expect(
      streamMessage(1, payload, vi.fn(), new AbortController().signal),
    ).rejects.toMatchObject({ name: 'AbortError' })
  })
})
