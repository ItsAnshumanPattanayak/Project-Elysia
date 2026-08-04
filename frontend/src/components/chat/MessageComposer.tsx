import type { StreamPhase } from '../../types/streaming'

export function MessageComposer({
  value,
  onChange,
  onSend,
  onCancel,
  phase,
  disabled,
  onRetry,
}: {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  onCancel: () => void
  phase: StreamPhase
  disabled: boolean
  onRetry: () => void
}) {
  const active = [
    'submitting',
    'accepted',
    'generating',
    'completing',
  ].includes(phase)
  return (
    <div className="composer-wrap">
      {phase === 'failed' && (
        <div className="generation-notice error" role="alert">
          <span>The response could not be completed.</span>
          <button onClick={onRetry}>Retry response</button>
        </div>
      )}
      {phase === 'cancelled' && (
        <div className="generation-notice">
          <span>
            Generation cancelled locally. The backend stops when it detects the
            disconnect.
          </span>
          <button onClick={onRetry}>Retry response</button>
        </div>
      )}
      <div className={`composer ${active ? 'active' : ''}`}>
        <textarea
          aria-label="Message Zara"
          placeholder={
            disabled ? 'This conversation is read-only' : 'Write to Zara…'
          }
          maxLength={10000}
          rows={1}
          value={value}
          disabled={disabled || active}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              if (value.trim() && !active && !disabled) onSend()
            }
          }}
        />
        <span className="character-count">
          {value.length.toLocaleString()} / 10,000
        </span>
        {active ? (
          <button
            className="cancel-generation"
            type="button"
            onClick={onCancel}
          >
            Cancel
          </button>
        ) : (
          <button
            className="send-button"
            type="button"
            aria-label="Send message"
            disabled={disabled || !value.trim()}
            onClick={onSend}
          >
            ↑
          </button>
        )}
      </div>
      <small className="composer-hint">
        Enter to send · Shift+Enter for a new line · Local AI may respond slowly
      </small>
    </div>
  )
}
