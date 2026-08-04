import { useEffect, useMemo, useRef, useState } from 'react'
import { friendlyError } from '../api/errors'
import { getAIStatus, listModels } from '../api/system'
import { ConfirmationDialog } from '../components/common/ConfirmationDialog'
import { Modal } from '../components/common/Modal'
import { useToast } from '../components/common/ToastProvider'
import { useApp } from '../state/AppContext'
import { defaultPreferences, useSettings } from '../state/SettingsContext'
import type { AIModel, AIStatus } from '../types/system'
import type { SettingValue, UiPreferences } from '../types/settings'

const categories = [
  ['general', 'General'],
  ['appearance', 'Appearance'],
  ['chat', 'Chat'],
  ['ai', 'AI & Ollama'],
  ['relationship', 'Relationship'],
  ['memory', 'Memory'],
  ['privacy', 'Privacy & local data'],
  ['about', 'About'],
] as const

function SelectField<T extends string>({
  label,
  value,
  options,
  description,
  onChange,
}: {
  label: string
  value: T
  options: Array<[T, string]>
  description?: string
  onChange: (value: T) => void
}) {
  const id = `field-${label.toLowerCase().replaceAll(' ', '-')}`
  return (
    <label className="setting-field" htmlFor={id}>
      <span>
        <strong>{label}</strong>
        {description && <small>{description}</small>}
      </span>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
      >
        {options.map(([key, text]) => (
          <option key={key} value={key}>
            {text}
          </option>
        ))}
      </select>
    </label>
  )
}

function ToggleField({
  label,
  description,
  checked,
  onChange,
}: {
  label: string
  description?: string
  checked: boolean
  onChange: (value: boolean) => void
}) {
  return (
    <label className="setting-field toggle-setting">
      <span>
        <strong>{label}</strong>
        {description && <small>{description}</small>}
      </span>
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
    </label>
  )
}

export function SettingsPage() {
  const {
    preferences,
    setPreference,
    resetPreferences,
    application,
    loading,
    error,
    saveApplication,
    resetApplication,
  } = useSettings()
  const { setDrawerOpen } = useApp()
  const notify = useToast()
  const [models, setModels] = useState<AIModel[]>([])
  const [status, setStatus] = useState<AIStatus | null>(null)
  const [aiError, setAIError] = useState('')
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState<Record<string, SettingValue>>({})
  const [resetAll, setResetAll] = useState(false)
  const [importPreview, setImportPreview] = useState<{
    preferences: Partial<UiPreferences>
    application: Record<string, SettingValue>
  } | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const values = useMemo(
    () => Object.fromEntries(application.map((item) => [item.key, item.value])),
    [application],
  )
  useEffect(() => setDraft(values), [values])
  useEffect(() => {
    const controller = new AbortController()
    void Promise.all([
      getAIStatus(false, controller.signal),
      listModels(false, controller.signal),
    ])
      .then(([nextStatus, nextModels]) => {
        setStatus(nextStatus)
        setModels(nextModels)
        setAIError('')
      })
      .catch((reason) => {
        if (!controller.signal.aborted) setAIError(friendlyError(reason))
      })
    return () => controller.abort()
  }, [])
  const setAppValue = (key: string, value: SettingValue) =>
    setDraft((current) => ({ ...current, [key]: value }))
  const saveCategory = async (category: string) => {
    const keys = application
      .filter((item) => item.category === category)
      .map((item) => item.key)
    const payload = Object.fromEntries(keys.map((key) => [key, draft[key]]))
    setBusy(true)
    try {
      await saveApplication(payload)
      notify('Settings saved')
    } catch (reason) {
      notify(friendlyError(reason), true)
    } finally {
      setBusy(false)
    }
  }
  const exportSettings = () => {
    const payload = {
      schema_version: 1,
      exported_at: new Date().toISOString(),
      preferences,
      application: values,
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'elysia-safe-settings.json'
    link.click()
    URL.revokeObjectURL(url)
    notify('Safe settings exported')
  }
  const readImport = async (file: File) => {
    try {
      const parsed: unknown = JSON.parse(await file.text())
      if (
        typeof parsed !== 'object' ||
        parsed === null ||
        !('schema_version' in parsed) ||
        parsed.schema_version !== 1
      )
        throw new Error('Unsupported settings schema version.')
      const record = parsed as Record<string, unknown>
      const allowedTop = new Set([
        'schema_version',
        'exported_at',
        'preferences',
        'application',
      ])
      const unknownTop = Object.keys(record).filter(
        (key) => !allowedTop.has(key),
      )
      if (unknownTop.length)
        throw new Error(`Unknown import key: ${unknownTop[0]}`)
      const importedPreferences =
        typeof record.preferences === 'object' && record.preferences !== null
          ? (record.preferences as Partial<UiPreferences>)
          : {}
      const unknownPreferences = Object.keys(importedPreferences).filter(
        (key) => !(key in defaultPreferences),
      )
      if (unknownPreferences.length)
        throw new Error(`Unsafe preference key: ${unknownPreferences[0]}`)
      const importedApplication =
        typeof record.application === 'object' && record.application !== null
          ? (record.application as Record<string, SettingValue>)
          : {}
      const allowedApplication = new Set(application.map((item) => item.key))
      const unknownApplication = Object.keys(importedApplication).filter(
        (key) => !allowedApplication.has(key),
      )
      if (unknownApplication.length)
        throw new Error(`Unsafe application setting: ${unknownApplication[0]}`)
      setImportPreview({
        preferences: importedPreferences,
        application: importedApplication,
      })
    } catch (reason) {
      notify(
        reason instanceof Error ? reason.message : 'Invalid settings file.',
        true,
      )
    }
  }
  const applyImport = async () => {
    if (!importPreview) return
    setBusy(true)
    try {
      for (const [key, value] of Object.entries(importPreview.preferences))
        setPreference(key as keyof UiPreferences, value as never)
      if (Object.keys(importPreview.application).length)
        await saveApplication(importPreview.application)
      setImportPreview(null)
      notify('Imported safe settings')
    } catch (reason) {
      notify(friendlyError(reason), true)
    } finally {
      setBusy(false)
    }
  }
  const ai = (key: string, fallback: number) => Number(draft[key] ?? fallback)
  return (
    <main className="settings-page dashboard-page">
      <header className="dashboard-header">
        <button
          className="icon-button mobile-menu"
          aria-label="Open navigation"
          onClick={() => setDrawerOpen(true)}
        >
          ☰
        </button>
        <div>
          <p className="overline">Local preferences</p>
          <h1>Settings</h1>
          <p>Safe controls for this browser and the local application.</p>
        </div>
        <div className="header-actions">
          <button className="button secondary" onClick={exportSettings}>
            Export
          </button>
          <button
            className="button secondary"
            onClick={() => fileInput.current?.click()}
          >
            Import
          </button>
          <button className="button danger" onClick={() => setResetAll(true)}>
            Reset all
          </button>
          <input
            ref={fileInput}
            className="visually-hidden"
            type="file"
            accept="application/json,.json"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void readImport(file)
              event.target.value = ''
            }}
          />
        </div>
      </header>
      <nav className="settings-navigation" aria-label="Settings sections">
        {categories.map(([id, text]) => (
          <a href={`#${id}`} key={id}>
            {text}
          </a>
        ))}
      </nav>
      {error && (
        <p className="error-panel" role="alert">
          {error}
        </p>
      )}
      <section id="general" className="settings-section">
        <div className="section-heading">
          <div>
            <h2>General</h2>
            <p>Identity and navigation preferences stored in this browser.</p>
          </div>
        </div>
        <label className="setting-field">
          <span>
            <strong>Display name</strong>
            <small>Used only in the local interface.</small>
          </span>
          <input
            maxLength={60}
            value={preferences.displayName}
            onChange={(event) =>
              setPreference('displayName', event.target.value)
            }
          />
        </label>
        <SelectField
          label="Default conversation page"
          value={preferences.defaultPage}
          options={[
            ['chat', 'Chat'],
            ['relationship', 'Relationship'],
            ['memories', 'Memories'],
          ]}
          onChange={(value) => setPreference('defaultPage', value)}
        />
        <SelectField
          label="Date and time"
          value={preferences.dateTime}
          options={[
            ['relative', 'Relative'],
            ['absolute', 'Absolute'],
          ]}
          onChange={(value) => setPreference('dateTime', value)}
        />
        <ToggleField
          label="Confirm destructive actions"
          checked={preferences.confirmDestructive}
          onChange={(value) => setPreference('confirmDestructive', value)}
        />
        <ToggleField
          label="Auto-open last conversation"
          checked={preferences.autoOpenLast}
          onChange={(value) => setPreference('autoOpenLast', value)}
        />
      </section>
      <section id="appearance" className="settings-section">
        <div className="section-heading">
          <div>
            <h2>Appearance</h2>
            <p>Changes apply immediately without reloading.</p>
          </div>
        </div>
        <SelectField
          label="Theme"
          value={preferences.theme}
          options={[
            ['system', 'System'],
            ['dark', 'Dark'],
            ['light', 'Light'],
          ]}
          onChange={(value) => setPreference('theme', value)}
        />
        <SelectField
          label="Accent"
          value={preferences.accent}
          options={[
            ['copper', 'Copper'],
            ['rose', 'Rose'],
            ['violet', 'Violet'],
            ['teal', 'Teal'],
          ]}
          onChange={(value) => setPreference('accent', value)}
        />
        <SelectField
          label="Density"
          value={preferences.density}
          options={[
            ['comfortable', 'Comfortable'],
            ['compact', 'Compact'],
          ]}
          onChange={(value) => setPreference('density', value)}
        />
        <SelectField
          label="Reduced motion"
          value={preferences.reducedMotion}
          options={[
            ['system', 'System'],
            ['enabled', 'Enabled'],
            ['disabled', 'Disabled'],
          ]}
          onChange={(value) => setPreference('reducedMotion', value)}
        />
        <SelectField
          label="Sidebar default"
          value={preferences.sidebarDefault}
          options={[
            ['expanded', 'Expanded'],
            ['collapsed', 'Collapsed'],
          ]}
          onChange={(value) => setPreference('sidebarDefault', value)}
        />
        <ToggleField
          label="Show relationship panel in chat"
          checked={preferences.relationshipPanel}
          onChange={(value) => setPreference('relationshipPanel', value)}
        />
        <div className="section-actions">
          <button className="button secondary" onClick={resetPreferences}>
            Reset appearance and UI
          </button>
        </div>
      </section>
      <section id="chat" className="settings-section">
        <div className="section-heading">
          <div>
            <h2>Chat</h2>
            <p>Composer, streaming, and message presentation.</p>
          </div>
        </div>
        <ToggleField
          label="Stream responses"
          description="When off, chat uses the existing non-stream local endpoint."
          checked={preferences.streaming}
          onChange={(value) => setPreference('streaming', value)}
        />
        <ToggleField
          label="Enter to send"
          checked={preferences.enterToSend}
          onChange={(value) => setPreference('enterToSend', value)}
        />
        <ToggleField
          label="Persist drafts"
          description="Turning this off removes saved local drafts as they are opened."
          checked={preferences.draftPersistence}
          onChange={(value) => setPreference('draftPersistence', value)}
        />
        <ToggleField
          label="Show timestamps"
          checked={preferences.showTimestamps}
          onChange={(value) => setPreference('showTimestamps', value)}
        />
        <ToggleField
          label="Show emotion badges"
          checked={preferences.showEmotionBadges}
          onChange={(value) => setPreference('showEmotionBadges', value)}
        />
        <ToggleField
          label="Show relationship event badges"
          checked={preferences.showRelationshipBadges}
          onChange={(value) => setPreference('showRelationshipBadges', value)}
        />
        <ToggleField
          label="Show memory processing indicator"
          checked={preferences.showMemoryIndicator}
          onChange={(value) => setPreference('showMemoryIndicator', value)}
        />
        <SelectField
          label="Auto-scroll"
          value={preferences.autoScroll}
          options={[
            ['always', 'Always'],
            ['smart', 'Smart'],
            ['disabled', 'Disabled'],
          ]}
          onChange={(value) => setPreference('autoScroll', value)}
        />
        <SelectField
          label="Language mode"
          value={preferences.languageMode}
          options={[
            ['auto', 'Automatic'],
            ['english', 'English'],
            ['hinglish', 'Hinglish'],
          ]}
          onChange={(value) => setPreference('languageMode', value)}
        />
        <SelectField
          label="Response length"
          value={
            String(draft.response_length ?? 'balanced') as
              | 'concise'
              | 'balanced'
              | 'detailed'
          }
          options={[
            ['concise', 'Concise'],
            ['balanced', 'Balanced'],
            ['detailed', 'Detailed'],
          ]}
          onChange={(value) => setAppValue('response_length', value)}
        />
        <div className="section-actions">
          <button
            className="button secondary"
            disabled={busy}
            onClick={() => void resetApplication({ category: 'chat' })}
          >
            Reset chat defaults
          </button>
          <button
            className="button"
            disabled={busy || loading}
            onClick={() => void saveCategory('chat')}
          >
            Save chat settings
          </button>
        </div>
      </section>
      <section id="ai" className="settings-section">
        <div className="section-heading">
          <div>
            <h2>AI and Ollama</h2>
            <p>Installed local models and bounded generation controls.</p>
          </div>
          {status && (
            <span
              className={`badge ${status.model_ready ? 'positive' : 'negative'}`}
            >
              {status.model_ready ? 'Ready' : status.state.replaceAll('_', ' ')}
            </span>
          )}
        </div>
        {aiError && <p className="error-panel">{aiError}</p>}
        <div className="status-grid">
          <div>
            <span>Service</span>
            <strong>{status?.available ? 'Available' : 'Unavailable'}</strong>
          </div>
          <div>
            <span>Version</span>
            <strong>{status?.version ?? 'Unknown'}</strong>
          </div>
          <div>
            <span>Configured model</span>
            <strong>{status?.configured_model ?? 'None'}</strong>
          </div>
          <div>
            <span>Operation</span>
            <strong>Local only</strong>
          </div>
        </div>
        <label className="setting-field">
          <span>
            <strong>Installed model</strong>
            <small>
              Only models reported by Ollama are selectable. This app never
              downloads a model.
            </small>
          </span>
          <select
            value={String(draft.selected_model ?? '')}
            onChange={(event) =>
              setAppValue('selected_model', event.target.value || null)
            }
          >
            <option value="">No model selected</option>
            {models.map((model) => (
              <option value={model.name} key={model.name}>
                {model.name} · {(model.size / 1_073_741_824).toFixed(1)} GB
              </option>
            ))}
          </select>
        </label>
        {String(draft.selected_model ?? '')
          .toLowerCase()
          .includes('llama3.1') && (
          <div className="warning-box">
            llama3.1:latest may be too heavy for this machine. Large local
            models can exhaust memory or respond slowly.
          </div>
        )}
        <div className="number-settings">
          {[
            ['temperature', 'Temperature', 0, 2, 0.1],
            ['top_p', 'Top-p', 0.01, 1, 0.01],
            ['top_k', 'Top-k', 1, 200, 1],
            ['repeat_penalty', 'Repeat penalty', 0.5, 2, 0.1],
            ['context_size', 'Context size', 512, 131072, 512],
            ['max_output_tokens', 'Output token limit', 32, 4096, 32],
          ].map(([key, text, min, max, step]) => (
            <label className="setting-field" key={String(key)}>
              <span>
                <strong>{String(text)}</strong>
                <small>
                  {min}–{max}
                </small>
              </span>
              <input
                type="number"
                min={min}
                max={max}
                step={step}
                value={ai(String(key), Number(min))}
                onChange={(event) =>
                  setAppValue(String(key), Number(event.target.value))
                }
              />
            </label>
          ))}
        </div>
        <div className="warning-box">
          <strong>Environment-controlled safety</strong>
          <p>
            Provider URL, credentials, hidden prompts, filesystem paths, and
            deployment limits are not editable here.
          </p>
        </div>
        <div className="section-actions">
          <button
            className="button secondary"
            disabled={busy}
            onClick={() => void resetApplication({ category: 'ai' })}
          >
            Reset AI defaults
          </button>
          <button
            className="button"
            disabled={busy || loading}
            onClick={() => void saveCategory('ai')}
          >
            Save AI settings
          </button>
        </div>
      </section>
      <section id="relationship" className="settings-section">
        <div className="section-heading">
          <div>
            <h2>Relationship</h2>
            <p>Global deterministic processing preference.</p>
          </div>
        </div>
        <ToggleField
          label="Relationship engine"
          description="Per-value locks remain controlled from each relationship dashboard."
          checked={Boolean(draft.relationship_engine_enabled)}
          onChange={(value) =>
            setAppValue('relationship_engine_enabled', value)
          }
        />
        <div className="section-actions">
          <button
            className="button secondary"
            onClick={() => void resetApplication({ category: 'relationship' })}
          >
            Reset
          </button>
          <button
            className="button"
            onClick={() => void saveCategory('relationship')}
          >
            Save
          </button>
        </div>
      </section>
      <section id="memory" className="settings-section">
        <div className="section-heading">
          <div>
            <h2>Memory</h2>
            <p>Automatic memory extraction preference.</p>
          </div>
        </div>
        <ToggleField
          label="Automatic memories"
          description="Manual memories are never removed by this preference."
          checked={Boolean(draft.auto_memory_enabled)}
          onChange={(value) => setAppValue('auto_memory_enabled', value)}
        />
        <div className="section-actions">
          <button
            className="button secondary"
            onClick={() => void resetApplication({ category: 'memory' })}
          >
            Reset
          </button>
          <button
            className="button"
            onClick={() => void saveCategory('memory')}
          >
            Save
          </button>
        </div>
      </section>
      <section id="privacy" className="settings-section">
        <div className="section-heading">
          <div>
            <h2>Privacy and local data</h2>
            <p>
              Project Elysia talks only to the local backend and local Ollama
              service.
            </p>
          </div>
        </div>
        <div className="privacy-grid">
          <article>
            <h3>Safe export</h3>
            <p>
              Includes UI, chat, and allow-listed application preferences. It
              excludes messages, memories, relationship history, credentials,
              paths, prompts, and environment values.
            </p>
          </article>
          <article>
            <h3>Reset boundaries</h3>
            <p>
              Resetting settings never resets conversations, messages, memories,
              relationship data, `.env`, or hard safety restrictions.
            </p>
          </article>
          <article>
            <h3>No remote sync</h3>
            <p>
              No cloud provider, telemetry service, model pull, or public
              hosting is introduced.
            </p>
          </article>
        </div>
      </section>
      <section id="about" className="settings-section">
        <div className="section-heading">
          <div>
            <h2>About</h2>
            <p>
              Project Elysia · Batch 7 relationship, memory, and settings
              dashboards.
            </p>
          </div>
        </div>
        <p className="modal-copy">
          The application is designed for one local user. Voice, image
          generation, authentication, cloud AI, synchronization, and packaging
          remain deliberately deferred.
        </p>
      </section>
      {resetAll && (
        <ConfirmationDialog
          title="Reset all safe settings?"
          consequence="All UI and allow-listed application settings will return to defaults. Conversations, memories, relationship data, .env, and hidden safety restrictions will not change."
          destructive
          confirmLabel="Reset safe settings"
          onCancel={() => setResetAll(false)}
          onConfirm={() => {
            setResetAll(false)
            setBusy(true)
            resetPreferences()
            void resetApplication({ all: true })
              .then(() => notify('All safe settings reset'))
              .catch((reason) => notify(friendlyError(reason), true))
              .finally(() => setBusy(false))
          }}
        />
      )}
      {importPreview && (
        <Modal title="Import preview" onClose={() => setImportPreview(null)}>
          <p className="modal-copy">
            Review the safe keys that will change. Unknown and unsafe keys have
            already been rejected.
          </p>
          <h3>UI preferences</h3>
          <pre className="technical-data">
            {JSON.stringify(importPreview.preferences, null, 2)}
          </pre>
          <h3>Application settings</h3>
          <pre className="technical-data">
            {JSON.stringify(importPreview.application, null, 2)}
          </pre>
          <div className="modal-actions">
            <button
              className="button secondary"
              onClick={() => setImportPreview(null)}
            >
              Cancel
            </button>
            <button
              className="button"
              disabled={busy}
              onClick={() => void applyImport()}
            >
              Confirm import
            </button>
          </div>
        </Modal>
      )}
    </main>
  )
}
