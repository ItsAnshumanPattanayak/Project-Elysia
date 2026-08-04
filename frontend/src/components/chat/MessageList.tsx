import { useLayoutEffect, useRef } from 'react'
import type { Message } from '../../types/message'
import { MessageBubble } from './MessageBubble'

export function MessageList({
  messages,
  hasOlder,
  loadingOlder,
  busy,
  onLoadOlder,
  onEdit,
  onDelete,
  onRegenerate,
}: {
  messages: Message[]
  hasOlder: boolean
  loadingOlder: boolean
  busy: boolean
  onLoadOlder: () => void
  onEdit: (message: Message, content: string) => void
  onDelete: (message: Message) => void
  onRegenerate: () => void
}) {
  const viewport = useRef<HTMLDivElement>(null)
  const previousHeight = useRef(0)
  useLayoutEffect(() => {
    if (!viewport.current) return
    if (previousHeight.current) {
      viewport.current.scrollTop +=
        viewport.current.scrollHeight - previousHeight.current
      previousHeight.current = 0
    }
  }, [messages.length])
  const loadOlder = () => {
    if (viewport.current) previousHeight.current = viewport.current.scrollHeight
    onLoadOlder()
  }
  return (
    <div className="message-viewport" ref={viewport}>
      <div className="message-list" aria-live="polite">
        {hasOlder && (
          <button
            className="load-older"
            disabled={loadingOlder}
            onClick={loadOlder}
          >
            {loadingOlder
              ? 'Loading earlier messages…'
              : 'Load earlier messages'}
          </button>
        )}
        {!hasOlder && messages.length > 0 && (
          <span className="history-start">Beginning of this conversation</span>
        )}
        {!messages.length && (
          <div className="chat-empty">
            <span>✦</span>
            <h2>A quiet moment with Zara</h2>
            <p>
              Write when you are ready. Messages and memories remain on this
              device.
            </p>
          </div>
        )}
        {messages.map((message, index) => (
          <MessageBubble
            key={message.id}
            message={message}
            latest={index === messages.length - 1}
            busy={busy}
            onEdit={onEdit}
            onDelete={onDelete}
            onRegenerate={onRegenerate}
          />
        ))}
      </div>
    </div>
  )
}
