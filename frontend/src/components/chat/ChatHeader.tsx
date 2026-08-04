import type { ConversationSummary } from '../../types/conversation'
import { ConversationActions } from '../conversations/ConversationActions'

export function ChatHeader({
  conversation,
  onMenu,
  onRefresh,
}: {
  conversation: ConversationSummary
  onMenu: () => void
  onRefresh: () => void
}) {
  return (
    <header className="chat-header">
      <button
        className="icon-button mobile-menu"
        aria-label="Open conversations"
        onClick={onMenu}
      >
        ☰
      </button>
      <span className="header-avatar">Z</span>
      <div className="chat-title">
        <strong>{conversation.title}</strong>
        <small>
          <i className="online-dot" /> Zara ·{' '}
          {conversation.relationship_stage.replaceAll('_', ' ')}
          {conversation.is_archived ? ' · archived' : ''}
        </small>
      </div>
      {conversation.current_scene && (
        <span className="scene" title={conversation.current_scene}>
          {conversation.current_scene}
        </span>
      )}
      <button
        className="icon-button"
        aria-label="Refresh conversation"
        onClick={onRefresh}
      >
        ↻
      </button>
      <ConversationActions conversation={conversation} />
    </header>
  )
}
