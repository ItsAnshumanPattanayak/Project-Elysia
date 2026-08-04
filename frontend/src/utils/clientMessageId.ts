export function clientMessageId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto)
    return `web:${crypto.randomUUID()}`
  return `web:${Date.now().toString(36)}:${Math.random().toString(36).slice(2, 10)}`
}
