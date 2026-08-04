import { NavLink, useLocation } from 'react-router-dom'
import { useApp } from '../../state/AppContext'
import { relativeDate } from '../../utils/dates'
import { ConversationActions } from './ConversationActions'
import { SystemStatusIndicator } from '../status/SystemStatusIndicator'

export function ConversationSidebar() {
  const location = useLocation()
  const matched = location.pathname.match(
    /^\/(?:chat|relationship|memories)\/(\d+)$/,
  )
  const activeConversationId = matched?.[1]
  const {
    conversations,
    loading,
    error,
    archived,
    setArchived,
    drawerOpen,
    setDrawerOpen,
    setNewDialogOpen,
    refresh,
  } = useApp()
  return (
    <aside
      className={`sidebar ${drawerOpen ? 'open' : ''}`}
      aria-label="Conversations"
    >
      <div className="sidebar-brand">
        <NavLink to="/" className="brand">
          <span className="mark">E</span>
          <span>
            <strong>Project Elysia</strong>
            <small>Private character space</small>
          </span>
        </NavLink>
        <button
          className="icon-button drawer-close"
          aria-label="Close conversations"
          onClick={() => setDrawerOpen(false)}
        >
          ×
        </button>
      </div>
      <nav className="workspace-navigation" aria-label="Workspace">
        {activeConversationId && (
          <>
            <NavLink
              to={`/chat/${activeConversationId}`}
              activeClassName="active"
              onClick={() => setDrawerOpen(false)}
            >
              Chat
            </NavLink>
            <NavLink
              to={`/relationship/${activeConversationId}`}
              activeClassName="active"
              onClick={() => setDrawerOpen(false)}
            >
              Relationship
            </NavLink>
            <NavLink
              to={`/memories/${activeConversationId}`}
              activeClassName="active"
              onClick={() => setDrawerOpen(false)}
            >
              Memories
            </NavLink>
          </>
        )}
        <NavLink
          exact
          to="/settings"
          activeClassName="active"
          onClick={() => setDrawerOpen(false)}
        >
          Settings
        </NavLink>
      </nav>
      <button
        className="new-conversation"
        type="button"
        onClick={() => setNewDialogOpen(true)}
      >
        <span>＋</span> New conversation
      </button>
      <div className="sidebar-filter">
        <button
          className={!archived ? 'active' : ''}
          onClick={() => setArchived(false)}
        >
          Recent
        </button>
        <button
          className={archived ? 'active' : ''}
          onClick={() => setArchived(true)}
        >
          Archived
        </button>
        <button
          className="icon-button"
          aria-label="Refresh conversations"
          onClick={() => void refresh()}
        >
          ↻
        </button>
      </div>
      <nav
        className="conversation-list"
        aria-label={
          archived ? 'Archived conversations' : 'Recent conversations'
        }
      >
        {loading &&
          [...Array(4)].map((_, index) => (
            <div className="conversation-skeleton" key={index} />
          ))}
        {!loading && error && (
          <div className="sidebar-empty" role="alert">
            <p>{error}</p>
            <button className="text-button" onClick={() => void refresh()}>
              Try again
            </button>
          </div>
        )}
        {!loading && !error && !conversations.length && (
          <div className="sidebar-empty">
            <span>✦</span>
            <p>
              {archived
                ? 'No archived conversations'
                : 'Your quiet space is ready.'}
            </p>
          </div>
        )}
        {conversations.map((conversation) => (
          <div className="conversation-row" key={conversation.id}>
            <NavLink
              to={`/chat/${conversation.id}`}
              activeClassName="active"
              onClick={() => setDrawerOpen(false)}
            >
              <span className="conversation-avatar">
                {conversation.character.display_name.slice(0, 1)}
              </span>
              <span className="conversation-copy">
                <strong title={conversation.title}>{conversation.title}</strong>
                <small>{relativeDate(conversation.last_message_at)}</small>
              </span>
              {conversation.is_archived && (
                <span className="archived-badge">Archived</span>
              )}
            </NavLink>
            <ConversationActions conversation={conversation} compact />
          </div>
        ))}
      </nav>
      <SystemStatusIndicator />
    </aside>
  )
}
