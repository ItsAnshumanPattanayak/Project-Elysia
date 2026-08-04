import { useState } from 'react'
import type { Message } from '../../types/message'
import { fullDate } from '../../utils/dates'
import { Modal } from '../common/Modal'

const safeEmotion = new Set([
  'neutral',
  'happy',
  'affectionate',
  'romantic',
  'playful',
  'concerned',
  'protective',
  'jealous',
  'angry',
  'hurt',
  'suspicious',
  'cold',
  'excited',
  'embarrassed',
  'relieved',
])

export function MessageBubble({
  message,
  latest,
  busy,
  onEdit,
  onDelete,
  onRegenerate,
}: {
  message: Message
  latest: boolean
  busy: boolean
  onEdit: (message: Message, content: string) => void
  onDelete: (message: Message) => void
  onRegenerate: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [content, setContent] = useState(message.raw_content)
  const character = message.sender === 'character'
  const emotion =
    message.emotion && safeEmotion.has(message.emotion) ? message.emotion : null
  return (
    <article
      className={`message ${message.sender} ${message.temporary ? 'temporary' : ''}`}
      aria-label={`${character ? 'Zara' : 'You'} message`}
    >
      <div className="message-meta">
        <strong>
          {character ? 'Zara' : message.sender === 'user' ? 'You' : 'System'}
        </strong>
        <time
          dateTime={message.created_at}
          title={fullDate(message.created_at)}
        >
          {fullDate(message.created_at)}
        </time>
        {message.is_edited && <span>edited</span>}
      </div>
      <div className="message-card">
        {character && message.narration && (
          <div className="narration">{message.narration}</div>
        )}
        {character && message.dialogue ? (
          <div className="dialogue">{message.dialogue}</div>
        ) : (
          <div className={character ? 'fallback-text' : 'user-text'}>
            {message.raw_content}
          </div>
        )}
        {emotion && <span className="emotion-badge">{emotion}</span>}
        {message.temporary && character && (
          <span className="typing-dots" aria-label="Zara is responding">
            <i />
            <i />
            <i />
          </span>
        )}
      </div>
      {!message.temporary && (
        <div className="message-actions">
          <button
            type="button"
            disabled={busy}
            onClick={() => onDelete(message)}
          >
            Delete
          </button>
          {message.sender === 'user' && (
            <button
              type="button"
              disabled={busy}
              onClick={() => setEditing(true)}
            >
              Edit
            </button>
          )}
          {latest && character && (
            <button type="button" disabled={busy} onClick={onRegenerate}>
              Regenerate
            </button>
          )}
        </div>
      )}
      {editing && (
        <Modal title="Edit your message" onClose={() => setEditing(false)}>
          <div className="form-stack">
            <label>
              Message
              <textarea
                rows={5}
                maxLength={10000}
                value={content}
                onChange={(event) => setContent(event.target.value)}
              />
            </label>
            <div className="modal-actions">
              <button
                className="button secondary"
                onClick={() => setEditing(false)}
              >
                Cancel
              </button>
              <button
                className="button"
                disabled={!content.trim()}
                onClick={() => {
                  onEdit(message, content.trim())
                  setEditing(false)
                }}
              >
                Save edit
              </button>
            </div>
          </div>
        </Modal>
      )}
    </article>
  )
}
