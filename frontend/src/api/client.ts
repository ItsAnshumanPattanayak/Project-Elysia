import { API_BASE_URL } from '../config/env'
import { AppApiError, normalizeApiError } from './errors'

export type Validator<T> = (value: unknown) => value is T

export async function requestJson<T>(
  path: string,
  validator: Validator<T>,
  init: RequestInit = {},
): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: init.body
        ? { 'Content-Type': 'application/json', ...init.headers }
        : init.headers,
    })
    if (!response.ok) throw await normalizeApiError(response)
    if (response.status === 204)
      throw new AppApiError(
        'empty_response',
        'The server returned no data.',
        204,
      )
    const value: unknown = await response.json()
    if (!validator(value))
      throw new AppApiError(
        'invalid_response',
        'The backend returned an unexpected response.',
        response.status,
      )
    return value
  } catch (error) {
    if (error instanceof AppApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError')
      throw new AppApiError('request_aborted', 'The request was cancelled.', 0)
    throw new AppApiError(
      'network_error',
      'The local backend could not be reached.',
      0,
      true,
      {},
      error,
    )
  }
}

export async function requestVoid(
  path: string,
  init: RequestInit = {},
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, init)
    if (!response.ok) throw await normalizeApiError(response)
    if (response.status !== 204)
      throw new AppApiError(
        'invalid_response',
        'Expected an empty successful response.',
        response.status,
      )
  } catch (error) {
    if (error instanceof AppApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError')
      throw new AppApiError('request_aborted', 'The request was cancelled.', 0)
    throw new AppApiError(
      'network_error',
      'The local backend could not be reached.',
      0,
      true,
      {},
      error,
    )
  }
}

export const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null
