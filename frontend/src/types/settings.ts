export type SettingValue = string | number | boolean | null

export interface SafeSetting {
  key: string
  value: SettingValue
  category: string
  is_default: boolean
  restart_required: boolean
}

export interface SettingsResponse {
  items: SafeSetting[]
  schema_version: 1
}

export interface SettingDefinition {
  key: string
  label: string
  category: string
  value_type: 'string' | 'integer' | 'number' | 'boolean' | 'enum' | 'model'
  default: SettingValue
  minimum: number | null
  maximum: number | null
  allowed_values: string[] | null
  restart_required: boolean
  description: string
}

export interface SettingsSchema {
  items: SettingDefinition[]
  schema_version: 1
}

export interface UiPreferences {
  displayName: string
  defaultPage: 'chat' | 'relationship' | 'memories'
  dateTime: 'relative' | 'absolute'
  confirmDestructive: boolean
  autoOpenLast: boolean
  theme: 'system' | 'dark' | 'light'
  accent: 'copper' | 'rose' | 'violet' | 'teal'
  density: 'comfortable' | 'compact'
  reducedMotion: 'system' | 'enabled' | 'disabled'
  sidebarDefault: 'expanded' | 'collapsed'
  relationshipPanel: boolean
  streaming: boolean
  enterToSend: boolean
  autoScroll: 'always' | 'smart' | 'disabled'
  draftPersistence: boolean
  showTimestamps: boolean
  showEmotionBadges: boolean
  showRelationshipBadges: boolean
  showMemoryIndicator: boolean
  languageMode: 'auto' | 'english' | 'hinglish'
}
