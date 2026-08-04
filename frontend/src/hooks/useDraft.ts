import { useEffect, useState } from 'react'

const MAX_DRAFT = 10_000
const key = (conversationId: number) => `elysia:draft:${conversationId}`

function readDraft(conversationId: number): string {
  try {
    return localStorage.getItem(key(conversationId))?.slice(0, MAX_DRAFT) ?? ''
  } catch {
    return ''
  }
}

export function useDraft(conversationId: number) {
  const [draft, setDraft] = useState(() => readDraft(conversationId))
  useEffect(() => setDraft(readDraft(conversationId)), [conversationId])
  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        if (draft)
          localStorage.setItem(key(conversationId), draft.slice(0, MAX_DRAFT))
        else localStorage.removeItem(key(conversationId))
      } catch {
        // Storage can be unavailable in private or locked-down browser contexts.
      }
    }, 180)
    return () => window.clearTimeout(timer)
  }, [conversationId, draft])
  const clear = () => {
    setDraft('')
    try {
      localStorage.removeItem(key(conversationId))
    } catch {
      // Keep the in-memory clear even if storage is unavailable.
    }
  }
  return { draft, setDraft, clear }
}
