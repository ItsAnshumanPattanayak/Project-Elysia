import { API_BASE_URL } from '../config/env'
import type { SendMessageRequest } from '../types/message'
import type { StreamEvent } from '../types/streaming'
import { SSEParser } from '../utils/sse'
import { AppApiError, normalizeApiError } from './errors'

export async function streamMessage(
  conversationId: number,
  payload: SendMessageRequest,
  onEvent: (event: StreamEvent) => void,
  signal: AbortSignal,
  maxCharacters = 50_000,
): Promise<void> {
  let response: Response
  try {
    response = await fetch(
      `${API_BASE_URL}/api/conversations/${conversationId}/messages/stream`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal,
      },
    )
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError')
      throw error
    throw new AppApiError(
      'network_error',
      'The local backend could not be reached.',
      0,
      true,
    )
  }
  if (!response.ok) throw await normalizeApiError(response)
  if (!response.body)
    throw new AppApiError(
      'stream_unsupported',
      'Streaming is unavailable.',
      response.status,
    )
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  const parser = new SSEParser()
  let outputCharacters = 0
  const deliver = (event: StreamEvent) => {
    if (event.event === 'token') {
      outputCharacters += String(event.data.text ?? '').length
      if (outputCharacters > maxCharacters)
        throw new AppApiError(
          'stream_output_limit',
          'The streamed response was too large.',
          0,
        )
    }
    onEvent(event)
  }
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      for (const event of parser.push(decoder.decode(value, { stream: true })))
        deliver(event)
    }
    for (const event of parser.push(decoder.decode())) deliver(event)
    for (const event of parser.finish()) deliver(event)
  } finally {
    reader.releaseLock()
  }
}
