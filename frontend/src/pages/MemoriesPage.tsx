import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getConversation } from '../api/conversations'
import { friendlyError } from '../api/errors'
import {
  createMemory,
  getMemory,
  listMemories,
  rebuildMemories,
  searchMemoryPreview,
  updateMemory,
} from '../api/memories'
import { ConfirmationDialog } from '../components/common/ConfirmationDialog'
import { Modal } from '../components/common/Modal'
import { useToast } from '../components/common/ToastProvider'
import { useApp } from '../state/AppContext'
import type { ConversationDetail } from '../types/conversation'
import type {
  ManualMemoryCreate,
  Memory,
  MemoryDetail,
  MemoryRebuild,
  MemorySearchPreview,
  MemoryType,
  MemoryUpdate,
} from '../types/memory'

const memoryTypes: MemoryType[] = [
  'user_fact',
  'user_preference',
  'user_dislike',
  'user_goal',
  'user_habit',
  'user_boundary',
  'user_relationship_fact',
  'shared_experience',
  'promise',
  'commitment',
  'conflict',
  'reconciliation',
  'emotional_moment',
  'character_fact',
  'scene_fact',
  'story_fact',
  'important_quote',
  'recurring_topic',
  'private_note',
]
const statuses = ['active', 'archived', 'superseded', 'reverted'] as const
const sources = [
  'model_candidate',
  'deterministic_user_fact',
  'manual',
  'consolidation',
  'system_rebuild',
]
const label = (value: string) =>
  value.replaceAll('_', ' ').replace(/^./, (item) => item.toUpperCase())

function MemoryForm({
  memory,
  busy,
  onClose,
  onSave,
}: {
  memory?: MemoryDetail
  busy: boolean
  onClose: () => void
  onSave: (payload: ManualMemoryCreate | MemoryUpdate) => Promise<void>
}) {
  const [content, setContent] = useState(memory?.content ?? '')
  const [type, setType] = useState<MemoryType>(
    memory?.memory_type ?? 'user_fact',
  )
  const [importance, setImportance] = useState(memory?.importance ?? 70)
  const [tags, setTags] = useState(memory?.tags.join(', ') ?? '')
  const [sensitive, setSensitive] = useState(memory?.is_sensitive ?? false)
  const [confirmedSensitive, setConfirmedSensitive] = useState(false)
  const [pinned, setPinned] = useState(memory?.is_pinned ?? false)
  const [locked, setLocked] = useState(memory?.is_locked ?? false)
  const [reason, setReason] = useState('')
  const [force, setForce] = useState(false)
  const [error, setError] = useState('')
  const submit = async () => {
    if (content.trim().length < 4) {
      setError('Memory content must contain at least 4 characters.')
      return
    }
    if (sensitive && !confirmedSensitive) {
      setError('Confirm that this sensitive memory should be stored locally.')
      return
    }
    if (memory && !reason.trim()) {
      setError('A reason is required for an edit audit entry.')
      return
    }
    setError('')
    const common = {
      content: content.trim(),
      memory_type: type,
      importance,
      tags: tags
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
        .slice(0, 10),
      sensitive,
      confirm_sensitive: sensitive && confirmedSensitive,
      pinned,
      locked,
    }
    await onSave(memory ? { ...common, reason: reason.trim(), force } : common)
  }
  return (
    <Modal
      title={memory ? 'Edit memory' : 'Create manual memory'}
      onClose={onClose}
    >
      <div className="form-stack">
        <label>
          Content
          <textarea
            data-autofocus
            rows={5}
            maxLength={1000}
            value={content}
            onChange={(event) => setContent(event.target.value)}
          />
          <span>{content.length} / 1,000</span>
        </label>
        <label>
          Memory type
          <select
            value={type}
            onChange={(event) => setType(event.target.value as MemoryType)}
          >
            {memoryTypes.map((item) => (
              <option value={item} key={item}>
                {label(item)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Importance (0–100)
          <input
            type="number"
            min="0"
            max="100"
            value={importance}
            onChange={(event) => setImportance(Number(event.target.value))}
          />
        </label>
        <label>
          Tags <span>Comma separated, up to 10</span>
          <input
            value={tags}
            onChange={(event) => setTags(event.target.value)}
          />
        </label>
        <p className="confirmed-field">
          Confidence: <strong>Confirmed (1.0)</strong>
        </p>
        <div className="toggle-grid">
          <label>
            <input
              type="checkbox"
              checked={pinned}
              onChange={(event) => setPinned(event.target.checked)}
            />{' '}
            Pinned
          </label>
          <label>
            <input
              type="checkbox"
              checked={locked}
              onChange={(event) => setLocked(event.target.checked)}
            />{' '}
            Locked
          </label>
          <label>
            <input
              type="checkbox"
              checked={sensitive}
              onChange={(event) => setSensitive(event.target.checked)}
            />{' '}
            Sensitive
          </label>
        </div>
        {sensitive && (
          <label className="check-field warning-box">
            <input
              type="checkbox"
              checked={confirmedSensitive}
              onChange={(event) => setConfirmedSensitive(event.target.checked)}
            />{' '}
            I understand this content is stored only in the local database.
          </label>
        )}
        {memory && (
          <>
            <label>
              Reason
              <textarea
                rows={2}
                maxLength={500}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
            {memory.is_locked && (
              <label className="check-field">
                <input
                  type="checkbox"
                  checked={force}
                  onChange={(event) => setForce(event.target.checked)}
                />{' '}
                Force a content/type change while locked
              </label>
            )}
          </>
        )}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </div>
      <div className="modal-actions">
        <button className="button secondary" onClick={onClose}>
          Cancel
        </button>
        <button
          className="button"
          disabled={busy}
          onClick={() => void submit()}
        >
          {busy ? 'Saving…' : memory ? 'Save changes' : 'Create memory'}
        </button>
      </div>
    </Modal>
  )
}

function MemoryDetailDialog({
  memory,
  busy,
  onClose,
  onEdit,
  onToggle,
  onArchive,
}: {
  memory: MemoryDetail
  busy: boolean
  onClose: () => void
  onEdit: () => void
  onToggle: (payload: MemoryUpdate) => Promise<void>
  onArchive: () => void
}) {
  return (
    <Modal title="Memory detail" onClose={onClose}>
      {memory.is_sensitive && (
        <div className="warning-box" role="note">
          <strong>Sensitive local memory</strong>
          <p>
            Review this content with care. It is never shown in global
            navigation.
          </p>
        </div>
      )}
      <p className="memory-full-content">{memory.content}</p>
      <dl className="detail-grid">
        <div>
          <dt>Type</dt>
          <dd>{label(memory.memory_type)}</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>{label(memory.source)}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{label(memory.status)}</dd>
        </div>
        <div>
          <dt>Importance</dt>
          <dd>{memory.importance}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{Math.round(memory.confidence * 100)}%</dd>
        </div>
        <div>
          <dt>Usage</dt>
          <dd>{memory.usage_count}</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{new Date(memory.created_at).toLocaleString()}</dd>
        </div>
        <div>
          <dt>Updated</dt>
          <dd>{new Date(memory.updated_at).toLocaleString()}</dd>
        </div>
        <div>
          <dt>Last used</dt>
          <dd>
            {memory.last_used_at
              ? new Date(memory.last_used_at).toLocaleString()
              : 'Never'}
          </dd>
        </div>
        <div>
          <dt>Tags</dt>
          <dd>{memory.tags.join(', ') || 'None'}</dd>
        </div>
        <div>
          <dt>Entities</dt>
          <dd>{memory.entities.join(', ') || 'None'}</dd>
        </div>
        <div>
          <dt>Source messages</dt>
          <dd>
            {[memory.source_user_message_id, memory.source_character_message_id]
              .filter(Boolean)
              .join(', ') || 'None'}
          </dd>
        </div>
        <div>
          <dt>Supersedes</dt>
          <dd>{memory.supersedes_memory_id ?? 'None'}</dd>
        </div>
        <div>
          <dt>Superseded by</dt>
          <dd>{memory.superseded_by_memory_id ?? 'None'}</dd>
        </div>
      </dl>
      <div className="badge-row">
        <span className="badge">
          {memory.is_pinned ? 'Pinned' : 'Not pinned'}
        </span>
        <span className="badge">
          {memory.is_locked ? 'Locked' : 'Unlocked'}
        </span>
      </div>
      <details>
        <summary>Development audit metadata</summary>
        <pre className="technical-data">
          {JSON.stringify(memory.memory_metadata, null, 2)}
        </pre>
      </details>
      <div className="modal-actions wrap">
        <button
          className="button secondary"
          disabled={busy}
          onClick={() =>
            void onToggle({
              pinned: !memory.is_pinned,
              reason: 'Pin state changed from memory dashboard.',
            })
          }
        >
          {memory.is_pinned ? 'Unpin' : 'Pin'}
        </button>
        <button
          className="button secondary"
          disabled={busy}
          onClick={() =>
            void onToggle({
              locked: !memory.is_locked,
              reason: 'Lock state changed from memory dashboard.',
            })
          }
        >
          {memory.is_locked ? 'Unlock' : 'Lock'}
        </button>
        <button
          className="button secondary"
          disabled={busy}
          onClick={onArchive}
        >
          {memory.status === 'archived' ? 'Unarchive' : 'Archive'}
        </button>
        <button className="button" onClick={onEdit}>
          Edit
        </button>
      </div>
    </Modal>
  )
}

function SearchPreview({
  conversationId,
  onClose,
}: {
  conversationId: number
  onClose: () => void
}) {
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(8)
  const [result, setResult] = useState<MemorySearchPreview | null>(null)
  const [error, setError] = useState('')
  return (
    <Modal title="Retrieval diagnostics" onClose={onClose}>
      <p className="modal-copy">
        Lexical local ranking only. These scores are diagnostics and are not
        sent into prompts. No network or embedding model is used.
      </p>
      <div className="form-stack">
        <label>
          Search query
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <label>
          Result limit
          <input
            type="number"
            min="1"
            max="30"
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          />
        </label>
        {error && <p className="form-error">{error}</p>}
      </div>
      <button
        className="button"
        disabled={!query.trim() || limit < 1 || limit > 30}
        onClick={() =>
          void searchMemoryPreview(conversationId, {
            query: query.trim(),
            limit,
          })
            .then(setResult)
            .catch((reason) => setError(friendlyError(reason)))
        }
      >
        Run local preview
      </button>
      {result && (
        <ol className="preview-results">
          {result.items.map((item, index) => (
            <li key={item.id}>
              <strong>
                #{index + 1} · {label(item.memory_type)} ·{' '}
                {item.score.final_score.toFixed(3)}
              </strong>
              <p>{item.content}</p>
              <dl className="score-grid">
                {Object.entries(item.score).map(([key, value]) => (
                  <div key={key}>
                    <dt>{label(key)}</dt>
                    <dd>{value.toFixed(3)}</dd>
                  </div>
                ))}
              </dl>
            </li>
          ))}
        </ol>
      )}
    </Modal>
  )
}

export function MemoriesPage() {
  const parameter = useParams<{ conversationId: string }>().conversationId
  const conversationId = Number(parameter)
  const valid = Number.isInteger(conversationId) && conversationId > 0
  const [conversation, setConversation] = useState<ConversationDetail | null>(
    null,
  )
  const [items, setItems] = useState<Memory[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [status, setStatus] = useState('active')
  const [type, setType] = useState('')
  const [source, setSource] = useState('')
  const [pinned, setPinned] = useState('all')
  const [locked, setLocked] = useState('all')
  const [sensitive, setSensitive] = useState('all')
  const [selected, setSelected] = useState<MemoryDetail | null>(null)
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState(false)
  const [confirmArchive, setConfirmArchive] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [confirmRebuild, setConfirmRebuild] = useState(false)
  const [rebuild, setRebuild] = useState<MemoryRebuild | null>(null)
  const searchController = useRef<AbortController | null>(null)
  const { setDrawerOpen } = useApp()
  const notify = useToast()
  useEffect(() => {
    const timer = window.setTimeout(
      () => setDebouncedSearch(search.trim()),
      300,
    )
    return () => window.clearTimeout(timer)
  }, [search])
  const filters = useMemo(
    () => ({
      status,
      type: type || undefined,
      source: source || undefined,
      pinned: pinned === 'all' ? undefined : pinned === 'yes',
      locked: locked === 'all' ? undefined : locked === 'yes',
      sensitive: sensitive === 'all' ? undefined : sensitive === 'yes',
      query: debouncedSearch || undefined,
      limit: 25,
    }),
    [status, type, source, pinned, locked, sensitive, debouncedSearch],
  )
  const loadCounts = useCallback(async () => {
    const [
      active,
      archived,
      superseded,
      reverted,
      pinnedCount,
      lockedCount,
      sensitiveCount,
    ] = await Promise.all([
      ...statuses.map((item) =>
        listMemories(conversationId, { status: item, limit: 1 }),
      ),
      listMemories(conversationId, { status: '', pinned: true, limit: 1 }),
      listMemories(conversationId, { status: '', locked: true, limit: 1 }),
      listMemories(conversationId, { status: '', sensitive: true, limit: 1 }),
    ])
    setCounts({
      active: active.total,
      archived: archived.total,
      superseded: superseded.total,
      reverted: reverted.total,
      pinned: pinnedCount.total,
      locked: lockedCount.total,
      sensitive: sensitiveCount.total,
      total: active.total + archived.total + superseded.total + reverted.total,
    })
  }, [conversationId])
  const loadList = useCallback(async () => {
    searchController.current?.abort()
    const controller = new AbortController()
    searchController.current = controller
    try {
      const result = await listMemories(
        conversationId,
        filters,
        controller.signal,
      )
      setItems(result.items)
      setTotal(result.total)
      setError('')
    } catch (reason) {
      if (!controller.signal.aborted) setError(friendlyError(reason))
    }
  }, [conversationId, filters])
  useEffect(() => {
    const controller = new AbortController()
    if (!valid) {
      setError('This conversation address is invalid.')
      setLoading(false)
      return () => controller.abort()
    }
    void Promise.all([
      getConversation(conversationId, controller.signal),
      loadCounts(),
    ])
      .then(([detail]) => {
        setConversation(detail)
        return loadList()
      })
      .catch((reason) => {
        if (!controller.signal.aborted) setError(friendlyError(reason))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => {
      controller.abort()
      searchController.current?.abort()
    }
  }, [conversationId, loadCounts, loadList, valid])
  useEffect(() => {
    if (!loading && valid) void loadList()
  }, [loadList, loading, valid])
  const refresh = async () => {
    await Promise.all([loadList(), loadCounts()])
    if (selected) setSelected(await getMemory(conversationId, selected.id))
  }
  const mutate = async (id: number, payload: MemoryUpdate) => {
    setBusy(true)
    try {
      const updated = await updateMemory(conversationId, id, payload)
      setSelected(updated)
      await refresh()
      notify('Memory updated')
    } catch (reason) {
      notify(friendlyError(reason), true)
      throw reason
    } finally {
      setBusy(false)
    }
  }
  if (loading)
    return (
      <main className="dashboard-state">
        <div className="spinner" />
        <p>Loading memory dashboard…</p>
      </main>
    )
  if (error && !conversation)
    return (
      <main className="dashboard-state">
        <h1>Memories unavailable</h1>
        <p>{error}</p>
        <Link className="button" to="/">
          Return home
        </Link>
      </main>
    )
  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <button
          className="icon-button mobile-menu"
          aria-label="Open navigation"
          onClick={() => setDrawerOpen(true)}
        >
          ☰
        </button>
        <div>
          <p className="overline">{conversation?.title}</p>
          <h1>Memories</h1>
          <p>Inspect and manage long-term memory stored on this device.</p>
        </div>
        <div className="header-actions">
          <button
            className="button secondary"
            disabled={busy}
            onClick={() => setConfirmRebuild(true)}
          >
            Rebuild
          </button>
          <button
            className="button secondary"
            onClick={() => setPreviewing(true)}
          >
            Retrieval preview
          </button>
          <button className="button" onClick={() => setCreating(true)}>
            New memory
          </button>
        </div>
      </header>
      <section className="count-grid" aria-label="Memory counts">
        {[
          'total',
          'active',
          'pinned',
          'locked',
          'archived',
          'superseded',
          'reverted',
          'sensitive',
        ].map((key) => (
          <article key={key}>
            <strong>{counts[key] ?? 0}</strong>
            <span>{label(key)}</span>
          </article>
        ))}
      </section>
      <section aria-labelledby="memory-list-title">
        <div className="section-heading">
          <div>
            <h2 id="memory-list-title">Memory library</h2>
            <p>
              {total} result{total === 1 ? '' : 's'}
            </p>
          </div>
        </div>
        <details className="mobile-filters" open>
          <summary>Search and filters</summary>
          <div className="filter-bar">
            <label>
              Search
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            <label>
              Status
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                <option value="">All</option>
                {statuses.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </label>
            <label>
              Type
              <select
                value={type}
                onChange={(event) => setType(event.target.value)}
              >
                <option value="">All</option>
                {memoryTypes.map((item) => (
                  <option key={item} value={item}>
                    {label(item)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Source
              <select
                value={source}
                onChange={(event) => setSource(event.target.value)}
              >
                <option value="">All</option>
                {sources.map((item) => (
                  <option key={item} value={item}>
                    {label(item)}
                  </option>
                ))}
              </select>
            </label>
            {[
              ['Pinned', pinned, setPinned],
              ['Locked', locked, setLocked],
              ['Sensitive', sensitive, setSensitive],
            ].map(([name, value, setter]) => (
              <label key={String(name)}>
                {String(name)}
                <select
                  value={String(value)}
                  onChange={(event) =>
                    (setter as (value: string) => void)(event.target.value)
                  }
                >
                  <option value="all">All</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </label>
            ))}
          </div>
        </details>
        {error && (
          <p className="error-panel" role="alert">
            {error}
          </p>
        )}
        {!items.length ? (
          <div className="empty-panel">No memories match these filters.</div>
        ) : (
          <div className="memory-list">
            {items.map((memory) => (
              <button
                className="memory-card"
                key={memory.id}
                onClick={() =>
                  void getMemory(conversationId, memory.id)
                    .then(setSelected)
                    .catch((reason) => notify(friendlyError(reason), true))
                }
              >
                <div className="memory-card-heading">
                  <strong>{label(memory.memory_type)}</strong>
                  <span className="badge">{label(memory.status)}</span>
                </div>
                <p>
                  {memory.is_sensitive
                    ? 'Sensitive memory — open to review'
                    : memory.content}
                </p>
                <div className="memory-meta">
                  <span>{label(memory.source)}</span>
                  <span>Importance {memory.importance}</span>
                  <span>{Math.round(memory.confidence * 100)}%</span>
                  <span>{memory.is_pinned ? 'Pinned' : ''}</span>
                  <span>{memory.is_locked ? 'Locked' : ''}</span>
                </div>
                <small>
                  Updated {new Date(memory.updated_at).toLocaleString()} · Used{' '}
                  {memory.usage_count} times
                </small>
              </button>
            ))}
          </div>
        )}
        {items.length < total && (
          <button
            className="button secondary load-more"
            onClick={async () => {
              const result = await listMemories(conversationId, {
                ...filters,
                offset: items.length,
              })
              setItems((current) => [...current, ...result.items])
            }}
          >
            Load more
          </button>
        )}
      </section>
      {creating && (
        <MemoryForm
          busy={busy}
          onClose={() => setCreating(false)}
          onSave={async (payload) => {
            setBusy(true)
            try {
              await createMemory(conversationId, payload as ManualMemoryCreate)
              setCreating(false)
              await refresh()
              notify('Manual memory created')
            } catch (reason) {
              notify(friendlyError(reason), true)
              throw reason
            } finally {
              setBusy(false)
            }
          }}
        />
      )}
      {selected && !editing && (
        <MemoryDetailDialog
          memory={selected}
          busy={busy}
          onClose={() => setSelected(null)}
          onEdit={() => setEditing(true)}
          onToggle={(payload) => mutate(selected.id, payload)}
          onArchive={() => setConfirmArchive(true)}
        />
      )}
      {selected && editing && (
        <MemoryForm
          memory={selected}
          busy={busy}
          onClose={() => setEditing(false)}
          onSave={async (payload) => {
            await mutate(selected.id, payload as MemoryUpdate)
            setEditing(false)
          }}
        />
      )}
      {previewing && (
        <SearchPreview
          conversationId={conversationId}
          onClose={() => setPreviewing(false)}
        />
      )}
      {selected && confirmArchive && (
        <ConfirmationDialog
          title={
            selected.status === 'archived'
              ? 'Unarchive this memory?'
              : 'Archive this memory?'
          }
          consequence={
            selected.status === 'archived'
              ? 'The memory will return to active prompt retrieval.'
              : `Archived memories are excluded from prompt retrieval.${
                  selected.is_locked
                    ? ' This locked memory requires this explicit force confirmation.'
                    : ''
                }`
          }
          confirmLabel={
            selected.status === 'archived' ? 'Unarchive' : 'Archive'
          }
          destructive={selected.status !== 'archived'}
          onCancel={() => setConfirmArchive(false)}
          onConfirm={() => {
            setConfirmArchive(false)
            void mutate(selected.id, {
              archived: selected.status !== 'archived',
              force: selected.is_locked,
              reason: `${selected.status === 'archived' ? 'Unarchived' : 'Archived'} from memory dashboard.`,
            })
          }}
        />
      )}
      {confirmRebuild && (
        <ConfirmationDialog
          title="Rebuild automatic memories?"
          consequence="No AI call is made. Manual memories are preserved; automatic memories are rebuilt from retained local messages and metadata. Relationship state and turn count do not change."
          confirmLabel="Rebuild locally"
          onCancel={() => setConfirmRebuild(false)}
          onConfirm={() => {
            setConfirmRebuild(false)
            setBusy(true)
            void rebuildMemories(conversationId)
              .then((result) => {
                setRebuild(result)
                return refresh()
              })
              .catch((reason) => notify(friendlyError(reason), true))
              .finally(() => setBusy(false))
          }}
        />
      )}
      {rebuild && (
        <Modal title="Memory rebuild complete" onClose={() => setRebuild(null)}>
          <div className="snapshot-grid">
            <div>
              <h3>Before</h3>
              <pre>{JSON.stringify(rebuild.before, null, 2)}</pre>
            </div>
            <div>
              <h3>After</h3>
              <pre>{JSON.stringify(rebuild.after, null, 2)}</pre>
            </div>
          </div>
          <ul>
            {rebuild.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
          <div className="modal-actions">
            <button className="button" onClick={() => setRebuild(null)}>
              Done
            </button>
          </div>
        </Modal>
      )}
    </main>
  )
}
