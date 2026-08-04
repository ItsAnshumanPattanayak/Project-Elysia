import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  createConversation,
  deleteConversation,
  listConversations,
  updateConversation,
} from '../api/conversations'
import { friendlyError } from '../api/errors'
import type {
  ConversationCreate,
  ConversationSummary,
  ConversationUpdate,
} from '../types/conversation'
import { useToast } from '../components/common/ToastProvider'

interface AppState {
  conversations: ConversationSummary[]
  loading: boolean
  error: string
  archived: boolean
  setArchived: (value: boolean) => void
  drawerOpen: boolean
  setDrawerOpen: (value: boolean) => void
  newDialogOpen: boolean
  setNewDialogOpen: (value: boolean) => void
  refresh: () => Promise<void>
  create: (payload: ConversationCreate) => Promise<ConversationSummary>
  update: (
    id: number,
    payload: ConversationUpdate,
  ) => Promise<ConversationSummary>
  remove: (id: number) => Promise<void>
}
const Context = createContext<AppState | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [archived, setArchived] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [newDialogOpen, setNewDialogOpen] = useState(false)
  const notify = useToast()
  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const result = await listConversations({ limit: 100, archived })
      setConversations(result.items)
      setError('')
    } catch (reason) {
      setError(friendlyError(reason))
    } finally {
      setLoading(false)
    }
  }, [archived])
  useEffect(() => void refresh(), [refresh])
  const create = useCallback(
    async (payload: ConversationCreate) => {
      const item = await createConversation(payload)
      setConversations((current) => [
        item,
        ...current.filter((entry) => entry.id !== item.id),
      ])
      notify('Conversation created')
      return item
    },
    [notify],
  )
  const update = useCallback(
    async (id: number, payload: ConversationUpdate) => {
      const item = await updateConversation(id, payload)
      setConversations((current) =>
        current
          .map((entry) => (entry.id === id ? item : entry))
          .filter((entry) => entry.is_archived === archived),
      )
      return item
    },
    [archived],
  )
  const remove = useCallback(
    async (id: number) => {
      await deleteConversation(id)
      setConversations((current) => current.filter((item) => item.id !== id))
      notify('Conversation deleted')
    },
    [notify],
  )
  const value = useMemo<AppState>(
    () => ({
      conversations,
      loading,
      error,
      archived,
      setArchived,
      drawerOpen,
      setDrawerOpen,
      newDialogOpen,
      setNewDialogOpen,
      refresh,
      create,
      update,
      remove,
    }),
    [
      conversations,
      loading,
      error,
      archived,
      drawerOpen,
      newDialogOpen,
      refresh,
      create,
      update,
      remove,
    ],
  )
  return <Context.Provider value={value}>{children}</Context.Provider>
}
// Keeping the provider and hook together prevents exposing the private context.
// eslint-disable-next-line react-refresh/only-export-components
export function useApp() {
  const value = useContext(Context)
  if (!value) throw new Error('useApp must be used within AppProvider')
  return value
}
