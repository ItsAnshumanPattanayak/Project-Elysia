import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getConversation } from '../api/conversations'
import { friendlyError } from '../api/errors'
import {
  getRelationship,
  listRelationshipEvents,
  recalculateRelationship,
  updateRelationship,
} from '../api/relationships'
import { ConfirmationDialog } from '../components/common/ConfirmationDialog'
import { Modal } from '../components/common/Modal'
import { useToast } from '../components/common/ToastProvider'
import { useApp } from '../state/AppContext'
import type { ConversationDetail } from '../types/conversation'
import type {
  RelationshipEvent,
  RelationshipRecalculation,
  RelationshipState,
  RelationshipUpdate,
} from '../types/relationship'

const metrics = [
  'attraction',
  'trust',
  'affection',
  'respect',
  'comfort',
  'jealousy',
  'anger',
] as const
const lockable = [...metrics, 'mood', 'relationship_stage'] as const
const moods = [
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
]
const stages = [
  'strangers',
  'acquaintances',
  'friends',
  'close_friends',
  'interested',
  'dating',
  'committed',
  'deeply_bonded',
  'strained',
  'separated',
]
const positiveEvents = new Set([
  'supportive',
  'affectionate',
  'romantic',
  'respectful',
  'honest',
  'vulnerable',
  'apologetic',
  'reassuring',
  'promise_kept',
  'conflict_resolved',
])
const negativeEvents = new Set([
  'rude',
  'dismissive',
  'dishonest',
  'manipulative',
  'jealous',
  'insensitive',
  'threatening',
  'promise_broken',
  'disrespectful',
  'trust_breach',
  'conflict_escalated',
  'emotionally_distant',
])

function label(value: string) {
  return value
    .replaceAll('_', ' ')
    .replace(/^./, (character) => character.toUpperCase())
}

function RelationshipEditor({
  state,
  busy,
  onClose,
  onSave,
}: {
  state: RelationshipState
  busy: boolean
  onClose: () => void
  onSave: (payload: RelationshipUpdate) => Promise<void>
}) {
  const [values, setValues] = useState(() =>
    Object.fromEntries(metrics.map((key) => [key, state[key]])),
  )
  const [mood, setMood] = useState(state.mood)
  const [stage, setStage] = useState(state.relationship_stage)
  const [locks, setLocks] = useState({ ...state.locked_values })
  const [reason, setReason] = useState('')
  const [force, setForce] = useState(false)
  const [error, setError] = useState('')
  const changesLocked = lockable.some((key) => {
    if (!state.locked_values[key]) return false
    if (key === 'mood') return mood !== state.mood
    if (key === 'relationship_stage') return stage !== state.relationship_stage
    return values[key] !== state[key]
  })
  const submit = async () => {
    if (!reason.trim()) {
      setError('A reason is required for the audit event.')
      return
    }
    if (changesLocked && !force) {
      setError('Confirm the explicit force override for changed locked values.')
      return
    }
    setError('')
    await onSave({
      ...values,
      mood,
      relationship_stage: stage,
      locked_values: locks,
      reason: reason.trim(),
      force,
    })
  }
  return (
    <Modal title="Update relationship" onClose={onClose}>
      <p className="modal-copy">
        Manual changes create a local audit event. Automatic processing cannot
        change locked values.
      </p>
      <div className="form-grid">
        {metrics.map((key) => (
          <label key={key}>
            {label(key)}{' '}
            {key === 'anger' || key === 'jealousy' ? '(negative)' : ''}
            <input
              type="number"
              min="0"
              max="100"
              value={values[key]}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  [key]: Number(event.target.value),
                }))
              }
            />
          </label>
        ))}
        <label>
          Mood
          <select
            value={mood}
            onChange={(event) => setMood(event.target.value)}
          >
            {moods.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Relationship stage
          <select
            value={stage}
            onChange={(event) => setStage(event.target.value)}
          >
            {stages.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
      </div>
      <fieldset className="toggle-grid">
        <legend>Automatic update locks</legend>
        {lockable.map((key) => (
          <label key={key}>
            <input
              type="checkbox"
              checked={Boolean(locks[key])}
              onChange={(event) =>
                setLocks((current) => ({
                  ...current,
                  [key]: event.target.checked,
                }))
              }
            />
            {label(key)}
          </label>
        ))}
      </fieldset>
      <label className="field">
        Reason
        <textarea
          rows={3}
          maxLength={500}
          value={reason}
          aria-describedby="relationship-reason-help"
          onChange={(event) => setReason(event.target.value)}
        />
        <small id="relationship-reason-help">
          Stored as safe audit evidence.
        </small>
      </label>
      {changesLocked && (
        <label className="check-field warning-box">
          <input
            type="checkbox"
            checked={force}
            onChange={(event) => setForce(event.target.checked)}
          />
          Force this manual change to locked values
        </label>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="modal-actions">
        <button className="button secondary" onClick={onClose}>
          Cancel
        </button>
        <button
          className="button"
          disabled={busy}
          onClick={() => void submit()}
        >
          {busy ? 'Saving…' : 'Save audit event'}
        </button>
      </div>
    </Modal>
  )
}

function EventItem({ event }: { event: RelationshipEvent }) {
  const category = positiveEvents.has(event.event_type)
    ? 'positive'
    : negativeEvents.has(event.event_type)
      ? 'negative'
      : 'neutral'
  return (
    <li className={`timeline-event ${event.is_reverted ? 'reverted' : ''}`}>
      <div className="timeline-heading">
        <strong>{label(event.event_type)}</strong>
        <span className={`badge ${category}`}>{category}</span>
        {event.is_reverted && <span className="badge">Reverted</span>}
        <time dateTime={event.created_at}>
          {new Date(event.created_at).toLocaleString()}
        </time>
      </div>
      <p>
        {label(event.source)} · {Math.round(event.confidence * 100)}% confidence
      </p>
      {!!Object.keys(event.score_deltas).length && (
        <dl className="delta-list">
          {Object.entries(event.score_deltas).map(([key, value]) => (
            <div key={key}>
              <dt>{label(key)}</dt>
              <dd>
                {value > 0 ? '+' : ''}
                {value}
              </dd>
            </div>
          ))}
        </dl>
      )}
      <p>
        {label(event.mood_before)} → {label(event.mood_after)} ·{' '}
        {label(event.stage_before)} → {label(event.stage_after)}
      </p>
      {event.evidence[0]?.description && (
        <p className="evidence">{event.evidence[0].description}</p>
      )}
      {(event.source_user_message_id || event.source_character_message_id) && (
        <small>
          Source messages:{' '}
          {[event.source_user_message_id, event.source_character_message_id]
            .filter(Boolean)
            .join(', ')}
        </small>
      )}
    </li>
  )
}

export function RelationshipPage() {
  const parameter = useParams<{ conversationId: string }>().conversationId
  const conversationId = Number(parameter)
  const valid = Number.isInteger(conversationId) && conversationId > 0
  const [conversation, setConversation] = useState<ConversationDetail | null>(
    null,
  )
  const [state, setState] = useState<RelationshipState | null>(null)
  const [events, setEvents] = useState<RelationshipEvent[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState(false)
  const [confirmRecalculate, setConfirmRecalculate] = useState(false)
  const [recalculation, setRecalculation] =
    useState<RelationshipRecalculation | null>(null)
  const [eventType, setEventType] = useState('')
  const [source, setSource] = useState('')
  const [status, setStatus] = useState('all')
  const [category, setCategory] = useState('all')
  const [oldestFirst, setOldestFirst] = useState(false)
  const { setDrawerOpen } = useApp()
  const notify = useToast()
  const load = useCallback(
    async (signal?: AbortSignal) => {
      if (!valid) {
        setError('This conversation address is invalid.')
        setLoading(false)
        return
      }
      setLoading(true)
      try {
        const [detail, relationship, history] = await Promise.all([
          getConversation(conversationId, signal),
          getRelationship(conversationId, signal),
          listRelationshipEvents(conversationId, { limit: 25 }, signal),
        ])
        setConversation(detail)
        setState(relationship)
        setEvents(history.items)
        setTotal(history.total)
        setError('')
      } catch (reason) {
        if (!signal?.aborted) setError(friendlyError(reason))
      } finally {
        if (!signal?.aborted) setLoading(false)
      }
    },
    [conversationId, valid],
  )
  useEffect(() => {
    const controller = new AbortController()
    void load(controller.signal)
    return () => controller.abort()
  }, [load])
  const filterEvents = useCallback(async () => {
    const result = await listRelationshipEvents(conversationId, {
      limit: 25,
      eventType: eventType || undefined,
      source: source || undefined,
      reverted: status === 'all' ? undefined : status === 'reverted',
      oldestFirst,
    })
    setEvents(result.items)
    setTotal(result.total)
  }, [conversationId, eventType, source, status, oldestFirst])
  useEffect(() => {
    if (valid)
      void filterEvents().catch((reason) => setError(friendlyError(reason)))
  }, [filterEvents, valid])
  const visibleEvents = useMemo(
    () =>
      events.filter((event) => {
        if (category === 'all') return true
        if (category === 'positive') return positiveEvents.has(event.event_type)
        if (category === 'negative') return negativeEvents.has(event.event_type)
        return (
          !positiveEvents.has(event.event_type) &&
          !negativeEvents.has(event.event_type)
        )
      }),
    [category, events],
  )
  const refresh = async () => {
    setState(await getRelationship(conversationId))
    await filterEvents()
  }
  if (loading)
    return (
      <main className="dashboard-state">
        <div className="spinner" />
        <p>Loading relationship dashboard…</p>
      </main>
    )
  if (error || !conversation || !state)
    return (
      <main className="dashboard-state">
        <h1>Relationship unavailable</h1>
        <p>{error || 'The conversation was not found.'}</p>
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
          <p className="overline">{conversation.title}</p>
          <h1>Relationship</h1>
          <p>Deterministic state and local audit history.</p>
        </div>
        <div className="header-actions">
          <button
            className="button secondary"
            disabled={busy}
            onClick={() => setConfirmRecalculate(true)}
          >
            Recalculate
          </button>
          <button
            className="button"
            disabled={busy}
            onClick={() => setEditing(true)}
          >
            Update
          </button>
        </div>
      </header>
      <section aria-labelledby="relationship-overview">
        <div className="section-heading">
          <div>
            <h2 id="relationship-overview">Current state</h2>
            <p>Updated {new Date(state.updated_at).toLocaleString()}</p>
          </div>
          <div className="badge-row">
            <span className="badge mood">{label(state.mood)}</span>
            <span className="badge">{label(state.relationship_stage)}</span>
            <span className="badge">Turn {state.turn_count}</span>
          </div>
        </div>
        <div className="metric-grid">
          {metrics.map((key) => (
            <article
              className={`metric-card ${key === 'anger' || key === 'jealousy' ? 'negative-metric' : ''}`}
              key={key}
            >
              <div>
                <h3>{label(key)}</h3>
                {state.locked_values[key] && (
                  <span
                    className="lock-label"
                    aria-label={`${label(key)} locked`}
                  >
                    Locked
                  </span>
                )}
              </div>
              <strong>{state[key]}</strong>
              <div
                className="progress"
                role="progressbar"
                aria-label={`${label(key)} ${state[key]} of 100`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={state[key]}
              >
                <i style={{ width: `${state[key]}%` }} />
              </div>
              {(key === 'anger' || key === 'jealousy') && (
                <small>Negative metric</small>
              )}
            </article>
          ))}
        </div>
      </section>
      <section aria-labelledby="event-history">
        <div className="section-heading">
          <div>
            <h2 id="event-history">Event history</h2>
            <p>
              {total} audited event{total === 1 ? '' : 's'}
            </p>
          </div>
        </div>
        <div className="filter-bar" aria-label="Relationship event filters">
          <label>
            Event type
            <input
              value={eventType}
              placeholder="e.g. supportive"
              onChange={(event) => setEventType(event.target.value)}
            />
          </label>
          <label>
            Source
            <select
              value={source}
              onChange={(event) => setSource(event.target.value)}
            >
              <option value="">All</option>
              <option value="deterministic">Deterministic</option>
              <option value="model_suggested_validated">
                Model suggestion (validated)
              </option>
              <option value="manual">Manual</option>
              <option value="system_recalculation">System recalculation</option>
            </select>
          </label>
          <label>
            Status
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              <option value="all">All</option>
              <option value="active">Active</option>
              <option value="reverted">Reverted</option>
            </select>
          </label>
          <label>
            Category
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              <option value="all">All</option>
              <option value="positive">Positive</option>
              <option value="neutral">Neutral</option>
              <option value="negative">Negative</option>
            </select>
          </label>
          <label>
            Order
            <select
              value={oldestFirst ? 'oldest' : 'newest'}
              onChange={(event) =>
                setOldestFirst(event.target.value === 'oldest')
              }
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
          </label>
        </div>
        {!visibleEvents.length ? (
          <div className="empty-panel">No events match these filters.</div>
        ) : (
          <ol className="timeline">
            {visibleEvents.map((event) => (
              <EventItem key={event.id} event={event} />
            ))}
          </ol>
        )}
        {events.length < total && (
          <button
            className="button secondary load-more"
            onClick={async () => {
              const result = await listRelationshipEvents(conversationId, {
                limit: 25,
                offset: events.length,
                eventType: eventType || undefined,
                source: source || undefined,
                reverted: status === 'all' ? undefined : status === 'reverted',
                oldestFirst,
              })
              setEvents((current) => [...current, ...result.items])
            }}
          >
            Load more
          </button>
        )}
      </section>
      {editing && (
        <RelationshipEditor
          state={state}
          busy={busy}
          onClose={() => setEditing(false)}
          onSave={async (payload) => {
            setBusy(true)
            try {
              await updateRelationship(conversationId, payload)
              await refresh()
              setEditing(false)
              notify('Relationship updated and audited')
            } catch (reason) {
              notify(friendlyError(reason), true)
              throw reason
            } finally {
              setBusy(false)
            }
          }}
        />
      )}
      {confirmRecalculate && (
        <ConfirmationDialog
          title="Recalculate relationship?"
          consequence="Replays the baseline and active event history locally. Messages, memories, and turn count remain unchanged. No AI model is called."
          confirmLabel="Recalculate"
          onCancel={() => setConfirmRecalculate(false)}
          onConfirm={() => {
            setConfirmRecalculate(false)
            setBusy(true)
            void recalculateRelationship(conversationId)
              .then((result) => {
                setRecalculation(result)
                return refresh()
              })
              .catch((reason) => notify(friendlyError(reason), true))
              .finally(() => setBusy(false))
          }}
        />
      )}
      {recalculation && (
        <Modal
          title="Recalculation complete"
          onClose={() => setRecalculation(null)}
        >
          <p className="modal-copy">
            Before: {label(recalculation.before.mood)} ·{' '}
            {label(recalculation.before.relationship_stage)}
          </p>
          <p className="modal-copy">
            After: {label(recalculation.after.mood)} ·{' '}
            {label(recalculation.after.relationship_stage)}
          </p>
          <ul>
            {recalculation.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
          <div className="modal-actions">
            <button className="button" onClick={() => setRecalculation(null)}>
              Done
            </button>
          </div>
        </Modal>
      )}
    </main>
  )
}
