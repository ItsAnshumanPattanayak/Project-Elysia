import type { ReactNode } from 'react'
import { ConversationSidebar } from '../components/conversations/ConversationSidebar'
import { NewConversationDialog } from '../components/conversations/NewConversationDialog'
import { useApp } from '../state/AppContext'

export function AppLayout({ children }: { children: ReactNode }) {
  const { drawerOpen, setDrawerOpen } = useApp()
  return (
    <div className="app-shell">
      <ConversationSidebar />
      {drawerOpen && (
        <button
          className="drawer-scrim"
          aria-label="Close conversations"
          onClick={() => setDrawerOpen(false)}
        />
      )}
      <div className="app-main">{children}</div>
      <NewConversationDialog />
    </div>
  )
}
