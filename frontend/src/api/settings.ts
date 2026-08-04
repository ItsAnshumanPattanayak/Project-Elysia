import type {
  SettingsResponse,
  SettingsSchema,
  SettingValue,
} from '../types/settings'
import { isObject, requestJson } from './client'

const isSettings = (value: unknown): value is SettingsResponse =>
  isObject(value) && value.schema_version === 1 && Array.isArray(value.items)
const isSchema = (value: unknown): value is SettingsSchema =>
  isObject(value) && value.schema_version === 1 && Array.isArray(value.items)

export const getSettings = (signal?: AbortSignal) =>
  requestJson<SettingsResponse>('/api/settings', isSettings, { signal })
export const getSettingsSchema = (signal?: AbortSignal) =>
  requestJson<SettingsSchema>('/api/settings/schema', isSchema, { signal })
export const updateSettings = (
  values: Record<string, SettingValue>,
  signal?: AbortSignal,
) =>
  requestJson<SettingsResponse>('/api/settings', isSettings, {
    method: 'PATCH',
    body: JSON.stringify({ values }),
    signal,
  })
export const resetSettings = (
  selector: { keys?: string[]; category?: string; all?: boolean },
  signal?: AbortSignal,
) =>
  requestJson<SettingsResponse>('/api/settings/reset', isSettings, {
    method: 'POST',
    body: JSON.stringify(selector),
    signal,
  })
