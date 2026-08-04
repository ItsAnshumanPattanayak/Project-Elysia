import { useState } from 'react'
import { useHistory } from 'react-router-dom'
import { friendlyError } from '../../api/errors'
import { useApp } from '../../state/AppContext'
import type { ConversationSummary } from '../../types/conversation'
import { ConfirmationDialog } from '../common/ConfirmationDialog'
import { Modal } from '../common/Modal'
import { useToast } from '../common/ToastProvider'

export function ConversationActions({
  conversation,
  compact = false,
}: {
  conversation: ConversationSummary
  compact?: boolean
}) {
  const [mode, setMode] = useState<'rename' | 'archive' | 'delete' | null>(null)
  const [title, setTitle] = useState(conversation.title)
  const [error, setError] = useState('')
  const { update, remove } = useApp()
  const notify = useToast()
  const history = useHistory()
  const rename = async () => {
    if (!title.trim()) return setError('Title cannot be empty.')
    try {
      await update(conversation.id, { title: title.trim() })
      notify('Conversation renamed')
      setMode(null)
    } catch (reason) {
      setError(friendlyError(reason))
      setTitle(conversation.title)
    }
  }
  const archive = async () => {
    try {
      await update(conversation.id, { is_archived: !conversation.is_archived })
      notify(
        conversation.is_archived
          ? 'Conversation restored'
          : 'Conversation archived',
      )
      setMode(null)
    } catch (reason) {
      notify(friendlyError(reason), true)
    }
  }
  const removeItem = async () => {
    try {
      await remove(conversation.id)
      setMode(null)
      history.push('/')
    } catch (reason) {
      notify(friendlyError(reason), true)
    }
  }
  return (
    <div className={`conversation-actions ${compact ? 'compact' : ''}`}>
      <button
        type="button"
        className="icon-button"
        aria-label={`Rename ${conversation.title}`}
        onClick={() => setMode('rename')}
      >
        ✎
      </button>
      <button
        type="button"
        className="icon-button"
        aria-label={
          conversation.is_archived
            ? 'Unarchive conversation'
            : 'Archive conversation'
        }
        onClick={() => setMode('archive')}
      >
        {conversation.is_archived ? '↗' : '⌁'}
      </button>
      <button
        type="button"
        className="icon-button danger-icon"
        aria-label="Delete conversation"
        onClick={() => setMode('delete')}
      >
        ×
      </button>
      {mode === 'rename' && (
        <Modal title="Rename conversation" onClose={() => setMode(null)}>
          <div className="form-stack">
            <label>
              Conversation title
              <input
                autoFocus
                maxLength={250}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') void rename()
                }}
              />
            </label>
            {error && (
              <p role="alert" className="form-error">
                {error}
              </p>
            )}
            <div className="modal-actions">
              <button
                className="button secondary"
                onClick={() => setMode(null)}
              >
                Cancel
              </button>
              <button className="button" onClick={() => void rename()}>
                Save
              </button>
            </div>
          </div>
        </Modal>
      )}
      {mode === 'archive' && (
        <ConfirmationDialog
          title={
            conversation.is_archived
              ? 'Restore conversation?'
              : 'Archive conversation?'
          }
          consequence={
            conversation.is_archived
              ? 'This conversation will become writable again.'
              : 'History remains available, but sending is disabled until restored.'
          }
          confirmLabel={conversation.is_archived ? 'Restore' : 'Archive'}
          onCancel={() => setMode(null)}
          onConfirm={() => void archive()}
        />
      )}
      {mode === 'delete' && (
        <ConfirmationDialog
          title="Delete this conversation?"
          consequence="Its messages, relationship history, and owned memories will be permanently deleted."
          confirmLabel="Delete conversation"
          destructive
          onCancel={() => setMode(null)}
          onConfirm={() => void removeItem()}
        />
      )}
    </div>
  )
}
