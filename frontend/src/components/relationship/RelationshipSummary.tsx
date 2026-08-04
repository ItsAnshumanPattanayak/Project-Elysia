import type { RelationshipState } from '../../types/relationship'

const fields = [
  'attraction',
  'trust',
  'affection',
  'respect',
  'comfort',
  'jealousy',
  'anger',
] as const
export function RelationshipSummary({
  relationship,
  memoryCount,
  selectedCount,
  loading,
}: {
  relationship: RelationshipState | null
  memoryCount: number
  selectedCount: number
  loading: boolean
}) {
  return (
    <aside className="insight-rail" aria-label="Conversation insights">
      <section className="insight-card relationship-card">
        <p className="overline">Relationship</p>
        {loading && <p className="muted">Reading the current state…</p>}
        {!loading && !relationship && (
          <p className="muted">Relationship state unavailable.</p>
        )}
        {relationship && (
          <>
            <div className="mood-heading">
              <span className="mood-orb" />
              <div>
                <strong>{relationship.mood.replaceAll('_', ' ')}</strong>
                <small>
                  {relationship.relationship_stage.replaceAll('_', ' ')} · turn{' '}
                  {relationship.turn_count}
                </small>
              </div>
            </div>
            <div className="relationship-values">
              {fields.map((field) => (
                <div key={field}>
                  <span>
                    <label>{field}</label>
                    <small>{relationship[field]}</small>
                  </span>
                  <div className="meter">
                    <i style={{ width: `${relationship[field]}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
      <section className="insight-card memory-summary">
        <p className="overline">Memory</p>
        <strong>
          {memoryCount} active recollection{memoryCount === 1 ? '' : 's'}
        </strong>
        <small>
          {selectedCount
            ? `${selectedCount} recalled for the latest response`
            : 'No recollections selected for the latest response'}
        </small>
        <span className="deferred-label">Full memory view · Batch 7</span>
      </section>
    </aside>
  )
}
