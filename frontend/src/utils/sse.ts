import type { StreamEvent, StreamEventName } from '../types/streaming'

const knownEvents = new Set<StreamEventName>([
  'accepted',
  'user_message',
  'start',
  'token',
  'metadata',
  'completed',
  'error',
  'cancelled',
])

export function parseSSEFrame(frame: string): StreamEvent | null {
  let event = 'message'
  const data: string[] = []
  for (const line of frame.replace(/\r/g, '').split('\n')) {
    if (!line || line.startsWith(':')) continue
    const separator = line.indexOf(':')
    const field = separator < 0 ? line : line.slice(0, separator)
    const value =
      separator < 0 ? '' : line.slice(separator + 1).replace(/^ /, '')
    if (field === 'event') event = value
    if (field === 'data') data.push(value)
  }
  if (!knownEvents.has(event as StreamEventName) || data.length === 0)
    return null
  try {
    const parsed: unknown = JSON.parse(data.join('\n'))
    if (typeof parsed !== 'object' || parsed === null) return null
    return {
      event: event as StreamEventName,
      data: parsed as Record<string, unknown>,
    }
  } catch {
    return null
  }
}

export class SSEParser {
  private buffer = ''
  push(chunk: string): StreamEvent[] {
    this.buffer += chunk
    const frames = this.buffer.replace(/\r\n/g, '\n').split('\n\n')
    this.buffer = frames.pop() ?? ''
    return frames.flatMap((frame) => {
      const parsed = parseSSEFrame(frame)
      return parsed ? [parsed] : []
    })
  }
  finish(): StreamEvent[] {
    const parsed = parseSSEFrame(this.buffer)
    this.buffer = ''
    return parsed ? [parsed] : []
  }
}
