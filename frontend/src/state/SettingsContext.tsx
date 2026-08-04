import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { getSettings, resetSettings, updateSettings } from '../api/settings'
import type {
  SafeSetting,
  SettingValue,
  UiPreferences,
} from '../types/settings'

const STORAGE_KEY = 'elysia:preferences:v1'
// Shared with the versioned import validator on the settings page.
// eslint-disable-next-line react-refresh/only-export-components
export const defaultPreferences: UiPreferences = {
  displayName: 'You',
  defaultPage: 'chat',
  dateTime: 'relative',
  confirmDestructive: true,
  autoOpenLast: true,
  theme: 'system',
  accent: 'copper',
  density: 'comfortable',
  reducedMotion: 'system',
  sidebarDefault: 'expanded',
  relationshipPanel: true,
  streaming: true,
  enterToSend: true,
  autoScroll: 'smart',
  draftPersistence: true,
  showTimestamps: true,
  showEmotionBadges: true,
  showRelationshipBadges: true,
  showMemoryIndicator: true,
  languageMode: 'auto',
}

function readPreferences(): UiPreferences {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}')
    if (typeof value !== 'object' || value === null) return defaultPreferences
    return { ...defaultPreferences, ...value }
  } catch {
    return defaultPreferences
  }
}

interface SettingsState {
  preferences: UiPreferences
  setPreference: <K extends keyof UiPreferences>(
    key: K,
    value: UiPreferences[K],
  ) => void
  resetPreferences: () => void
  application: SafeSetting[]
  loading: boolean
  error: string
  refresh: () => Promise<void>
  saveApplication: (values: Record<string, SettingValue>) => Promise<void>
  resetApplication: (selector: {
    keys?: string[]
    category?: string
    all?: boolean
  }) => Promise<void>
}

const Context = createContext<SettingsState | null>(null)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState(readPreferences)
  const [application, setApplication] = useState<SafeSetting[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      setApplication((await getSettings()).items)
      setError('')
    } catch {
      setError('Safe application settings are unavailable.')
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => void refresh(), [refresh])
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences))
    } catch {
      setError('UI preferences could not be saved in this browser.')
    }
    const root = document.documentElement
    root.dataset.theme = preferences.theme
    root.dataset.accent = preferences.accent
    root.dataset.density = preferences.density
    root.dataset.motion = preferences.reducedMotion
    root.dataset.timestamps = preferences.showTimestamps ? 'show' : 'hide'
    root.dataset.emotions = preferences.showEmotionBadges ? 'show' : 'hide'
  }, [preferences])
  const setPreference = useCallback(
    <K extends keyof UiPreferences>(key: K, value: UiPreferences[K]) =>
      setPreferences((current) => ({ ...current, [key]: value })),
    [],
  )
  const resetPreferences = useCallback(() => {
    setPreferences(defaultPreferences)
  }, [])
  const saveApplication = useCallback(
    async (values: Record<string, SettingValue>) => {
      setApplication((await updateSettings(values)).items)
    },
    [],
  )
  const resetApplication = useCallback(
    async (selector: { keys?: string[]; category?: string; all?: boolean }) => {
      setApplication((await resetSettings(selector)).items)
    },
    [],
  )
  const value = useMemo(
    () => ({
      preferences,
      setPreference,
      resetPreferences,
      application,
      loading,
      error,
      refresh,
      saveApplication,
      resetApplication,
    }),
    [
      preferences,
      setPreference,
      resetPreferences,
      application,
      loading,
      error,
      refresh,
      saveApplication,
      resetApplication,
    ],
  )
  return <Context.Provider value={value}>{children}</Context.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSettings() {
  const value = useContext(Context)
  if (!value)
    throw new Error('useSettings must be used within SettingsProvider')
  return value
}
