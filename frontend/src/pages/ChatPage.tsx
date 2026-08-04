import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from 'react'
import { useParams } from 'react-router-dom'
import { getConversation } from '../api/conversations'
import { AppApiError, friendlyError } from '../api/errors'
import { listMemories } from '../api/memories'
import {
  deleteMessage,
  editMessage,
  listMessages,
  regenerateMessage,
  sendMessage,
} from '../api/messages'
import { getRelationship } from '../api/relationships'
import { streamMessage } from '../api/streaming'
import { ChatHeader } from '../components/chat/ChatHeader'
import { MessageComposer } from '../components/chat/MessageComposer'
import { MessageList } from '../components/chat/MessageList'
import { ConfirmationDialog } from '../components/common/ConfirmationDialog'
import { useToast } from '../components/common/ToastProvider'
import { RelationshipSummary } from '../components/relationship/RelationshipSummary'
import { useDraft } from '../hooks/useDraft'
import { useApp } from '../state/AppContext'
import { useSettings } from '../state/SettingsContext'
import { chatReducer, initialStreamState } from '../state/chatReducer'
import type { ConversationDetail } from '../types/conversation'
import type { Message } from '../types/message'
import type { RelationshipState } from '../types/relationship'
import { clientMessageId } from '../utils/clientMessageId'
import { isMessage } from '../api/guards'

type PendingAction =
  | { kind: 'delete'; message: Message; truncate?: boolean }
  | { kind: 'edit'; message: Message; content: string }
  | { kind: 'regenerate' }

const activePhases = new Set([
  'submitting',
  'accepted',
  'generating',
  'completing',
])

export function ChatPage() {
  const parameter = useParams<{ conversationId: string }>().conversationId
  const conversationId = Number(parameter)
  const validId = Number.isInteger(conversationId) && conversationId > 0
  const [conversation, setConversation] = useState<ConversationDetail | null>(
    null,
  )
  const [messages, setMessages] = useState<Message[]>([])
  const [relationship, setRelationship] = useState<RelationshipState | null>(
    null,
  )
  const [memoryCount, setMemoryCount] = useState(0)
  const [offset, setOffset] = useState(0)
  const [hasOlder, setHasOlder] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [error, setError] = useState('')
  const [state, dispatch] = useReducer(chatReducer, initialStreamState)
  const [pending, setPending] = useState<PendingAction | null>(null)
  const streamController = useRef<AbortController | null>(null)
  const { preferences } = useSettings()
  const { draft, setDraft, clear } = useDraft(
    validId ? conversationId : 0,
    preferences.draftPersistence,
  )
  const { setDrawerOpen, refresh: refreshSidebar } = useApp()
  const notify = useToast()

  const load = useCallback(
    async (signal?: AbortSignal) => {
      if (!validId) {
        setError('This conversation address is invalid.')
        setLoading(false)
        return
      }
      setLoading(true)
      try {
        const detail = await getConversation(conversationId, signal)
        const start = Math.max(0, detail.message_count - 50)
        const [history, relation, memories] = await Promise.all([
          listMessages(conversationId, { offset: start, limit: 50 }, signal),
          getRelationship(conversationId, signal).catch(() => null),
          listMemories(
            conversationId,
            { status: 'active', limit: 1 },
            signal,
          ).catch(() => null),
        ])
        setConversation(detail)
        setMessages(history.items)
        setRelationship(relation)
        setMemoryCount(memories?.total ?? 0)
        setOffset(start)
        setHasOlder(start > 0)
        setError('')
      } catch (reason) {
        setError(friendlyError(reason))
      } finally {
        setLoading(false)
      }
    },
    [conversationId, validId],
  )

  const refreshRelated = useCallback(async () => {
    if (!validId) return
    const [detail, relation, memories] = await Promise.all([
      getConversation(conversationId),
      getRelationship(conversationId).catch(() => null),
      listMemories(conversationId, { status: 'active', limit: 1 }).catch(
        () => null,
      ),
    ])
    setConversation(detail)
    setRelationship(relation)
    setMemoryCount(memories?.total ?? 0)
    await refreshSidebar()
  }, [conversationId, refreshSidebar, validId])

  const refreshMessages = useCallback(async () => {
    if (!conversation) return
    const start = Math.max(0, conversation.message_count - 50)
    const history = await listMessages(conversationId, {
      offset: start,
      limit: 50,
    })
    setMessages(history.items)
    setOffset(start)
    setHasOlder(start > 0)
  }, [conversation, conversationId])

  useEffect(() => {
    const controller = new AbortController()
    streamController.current?.abort()
    dispatch({ type: 'reset' })
    void load(controller.signal)
    return () => {
      controller.abort()
      streamController.current?.abort()
    }
  }, [load])

  const addOptimistic = (content: string) => {
    const sequence =
      Math.max(0, ...messages.map((item) => item.sequence_number)) + 1
    const now = new Date().toISOString()
    const user: Message = {
      id: `temp-user-${Date.now()}`,
      conversation_id: conversationId,
      sender: 'user',
      raw_content: content,
      narration: null,
      dialogue: null,
      emotion: null,
      message_metadata: {},
      sequence_number: sequence,
      is_edited: false,
      created_at: now,
      edited_at: null,
      temporary: true,
    }
    const character: Message = {
      ...user,
      id: `temp-character-${Date.now()}`,
      sender: 'character',
      raw_content: '',
      sequence_number: sequence + 1,
    }
    setMessages((current) => [...current, user, character])
  }

  const reconcileUser = (message: Message) =>
    setMessages((current) =>
      current.map((item) =>
        String(item.id).startsWith('temp-user-') ? message : item,
      ),
    )
  const reconcileCharacter = (message: Message) =>
    setMessages((current) =>
      current.map((item) =>
        String(item.id).startsWith('temp-character-') ? message : item,
      ),
    )
  const removeTemporaryCharacter = () =>
    setMessages((current) =>
      current.filter((item) => !String(item.id).startsWith('temp-character-')),
    )

  const submit = async (contentOverride?: string) => {
    if (!conversation || activePhases.has(state.phase)) return
    const content = (contentOverride ?? draft).trim()
    if (!content) return
    dispatch({ type: 'submit', conversationId, content })
    addOptimistic(content)
    const payload = {
      content,
      client_message_id: clientMessageId(),
      language_mode:
        preferences.languageMode === 'auto'
          ? undefined
          : preferences.languageMode,
    }
    const controller = new AbortController()
    streamController.current = controller
    let accepted = false
    let completed = false
    try {
      if (!preferences.streaming || typeof ReadableStream === 'undefined') {
        const result = await sendMessage(
          conversationId,
          payload,
          controller.signal,
        )
        accepted = true
        clear()
        reconcileUser(result.user_message)
        reconcileCharacter(result.character_message)
        completed = true
        dispatch({ type: 'complete' })
        result.warnings.forEach((warning) => notify(warning, true))
      } else {
        await streamMessage(
          conversationId,
          payload,
          (event) => {
            if (event.event === 'accepted') {
              accepted = true
              clear()
              dispatch({ type: 'accepted' })
            } else if (
              event.event === 'user_message' &&
              isMessage(event.data)
            ) {
              reconcileUser(event.data)
              dispatch({ type: 'user', message: event.data })
            } else if (event.event === 'start') dispatch({ type: 'start' })
            else if (event.event === 'token')
              dispatch({ type: 'token', text: String(event.data.text ?? '') })
            else if (event.event === 'metadata') {
              dispatch({ type: 'metadata', data: event.data })
              const warnings = event.data.warnings
              if (Array.isArray(warnings))
                warnings
                  .filter((item): item is string => typeof item === 'string')
                  .forEach((warning) => notify(warning, true))
            } else if (event.event === 'completed') {
              dispatch({ type: 'completing' })
              if (isMessage(event.data.character_message))
                reconcileCharacter(event.data.character_message)
              completed = true
              dispatch({ type: 'complete' })
            } else if (event.event === 'error')
              throw new AppApiError(
                String(event.data.code ?? 'stream_error'),
                String(event.data.message ?? 'Generation failed.'),
                0,
                event.data.retryable === true,
              )
            else if (event.event === 'cancelled') dispatch({ type: 'cancel' })
          },
          controller.signal,
        )
      }
      if (!completed) {
        removeTemporaryCharacter()
        dispatch({
          type: 'fail',
          message: 'The stream ended before completion.',
        })
      } else await refreshRelated()
    } catch (reason) {
      removeTemporaryCharacter()
      if (controller.signal.aborted) dispatch({ type: 'cancel' })
      else dispatch({ type: 'fail', message: friendlyError(reason) })
      if (accepted) {
        clear()
        await refreshMessages().catch(() => undefined)
      }
    } finally {
      streamController.current = null
    }
  }

  const regenerate = async () => {
    try {
      const result = await regenerateMessage(conversationId)
      setMessages((current) => {
        const withoutSame = current.filter(
          (item) => item.id !== result.character_message.id,
        )
        return [...withoutSame, result.character_message].sort(
          (a, b) => a.sequence_number - b.sequence_number,
        )
      })
      result.warnings.forEach((warning) => notify(warning, true))
      notify('Response regenerated')
      dispatch({ type: 'reset' })
      await refreshRelated()
    } catch (reason) {
      notify(friendlyError(reason), true)
    } finally {
      setPending(null)
    }
  }

  const edit = async (message: Message, content: string, confirm = false) => {
    try {
      await editMessage(conversationId, Number(message.id), content, confirm)
      notify('Edit saved')
      setPending(null)
      await load()
    } catch (reason) {
      if (
        reason instanceof AppApiError &&
        reason.code === 'message_edit_requires_truncation'
      )
        setPending({ kind: 'edit', message, content })
      else notify(friendlyError(reason), true)
    }
  }
  const remove = async (message: Message, confirm = false) => {
    try {
      await deleteMessage(conversationId, Number(message.id), confirm)
      notify('Message deleted')
      setPending(null)
      await load()
    } catch (reason) {
      if (
        reason instanceof AppApiError &&
        reason.code === 'message_delete_requires_truncation'
      )
        setPending({ kind: 'delete', message, truncate: true })
      else notify(friendlyError(reason), true)
    }
  }
  const loadOlder = async () => {
    if (!hasOlder || loadingOlder) return
    setLoadingOlder(true)
    try {
      const start = Math.max(0, offset - 50)
      const result = await listMessages(conversationId, {
        offset: start,
        limit: offset - start,
      })
      setMessages((current) => [
        ...result.items,
        ...current.filter(
          (item) => !result.items.some((older) => older.id === item.id),
        ),
      ])
      setOffset(start)
      setHasOlder(start > 0)
    } catch (reason) {
      notify(friendlyError(reason), true)
    } finally {
      setLoadingOlder(false)
    }
  }
  const selectedCount = useMemo(() => {
    const latest = [...messages]
      .reverse()
      .find((item) => item.sender === 'character')
    const selected = latest?.message_metadata.selected_memory_ids
    return Array.isArray(selected) ? selected.length : 0
  }, [messages])
  const busy = activePhases.has(state.phase)
  if (loading)
    return (
      <main className="chat-loading" role="status">
        <span className="spinner" />
        Opening conversation…
      </main>
    )
  if (error || !conversation)
    return (
      <main className="chat-error">
        <p className="overline">Conversation unavailable</p>
        <h1>{error || 'This conversation was not found.'}</h1>
        <button className="button" onClick={() => void load()}>
          Try again
        </button>
      </main>
    )
  return (
    <main className="chat-page">
      <ChatHeader
        conversation={conversation}
        onMenu={() => setDrawerOpen(true)}
        onRefresh={() => void load()}
      />
      <div className="chat-body">
        <section className="chat-column">
          <MessageList
            messages={
              state.text
                ? messages.map((item) =>
                    String(item.id).startsWith('temp-character-')
                      ? { ...item, raw_content: state.text }
                      : item,
                  )
                : messages
            }
            hasOlder={hasOlder}
            loadingOlder={loadingOlder}
            busy={busy}
            onLoadOlder={() => void loadOlder()}
            onEdit={(message, content) => void edit(message, content)}
            onDelete={(message) => setPending({ kind: 'delete', message })}
            onRegenerate={() => setPending({ kind: 'regenerate' })}
          />
          <div className="stream-announcer" aria-live="polite">
            {state.phase === 'generating'
              ? 'Zara is responding'
              : state.phase === 'completed'
                ? 'Response completed'
                : state.phase === 'failed'
                  ? state.error
                  : state.phase === 'cancelled'
                    ? 'Generation cancelled'
                    : ''}
          </div>
          <MessageComposer
            value={draft}
            onChange={setDraft}
            onSend={() => void submit()}
            onCancel={() => streamController.current?.abort()}
            phase={state.phase}
            disabled={conversation.is_archived || !conversation.is_active}
            onRetry={() =>
              state.persistedUser
                ? void regenerate()
                : void submit(state.retryContent ?? draft)
            }
            enterToSend={preferences.enterToSend}
          />
        </section>
        {preferences.relationshipPanel && (
          <RelationshipSummary
            relationship={relationship}
            memoryCount={memoryCount}
            selectedCount={selectedCount}
            loading={false}
          />
        )}
      </div>
      {pending?.kind === 'regenerate' && (
        <ConfirmationDialog
          title="Regenerate Zara's response?"
          consequence="The current latest response and its derived relationship and memory effects will be replaced only if generation succeeds."
          confirmLabel="Regenerate"
          onCancel={() => setPending(null)}
          onConfirm={() => void regenerate()}
        />
      )}
      {pending?.kind === 'edit' && (
        <ConfirmationDialog
          title="Edit and truncate later history?"
          consequence="Editing this message will remove all later messages and revert their derived relationship and memory effects."
          confirmLabel="Edit and truncate"
          destructive
          onCancel={() => setPending(null)}
          onConfirm={() => void edit(pending.message, pending.content, true)}
        />
      )}
      {pending?.kind === 'delete' && (
        <ConfirmationDialog
          title={
            pending.truncate
              ? 'Delete and truncate later history?'
              : 'Delete this message?'
          }
          consequence="The message and any later dependent messages, relationship effects, and automatic memories may be removed or reverted."
          confirmLabel="Delete message"
          destructive
          onCancel={() => setPending(null)}
          onConfirm={() =>
            void remove(pending.message, pending.truncate ?? false)
          }
        />
      )}
    </main>
  )
}
