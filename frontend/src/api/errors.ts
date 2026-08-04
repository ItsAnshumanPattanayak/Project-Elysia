const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

export class AppApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
    public readonly retryable = false,
    public readonly details: Record<string, unknown> = {},
    public readonly cause?: unknown,
  ) {
    super(message)
    this.name = 'AppApiError'
  }
}

export async function normalizeApiError(
  response: Response,
): Promise<AppApiError> {
  try {
    const value: unknown = await response.json()
    if (isObject(value) && isObject(value.error)) {
      const error = value.error
      return new AppApiError(
        typeof error.code === 'string' ? error.code : 'unknown_error',
        typeof error.message === 'string'
          ? error.message
          : 'The request could not be completed.',
        response.status,
        error.retryable === true,
        isObject(error.details) ? error.details : {},
      )
    }
  } catch {
    // Non-JSON error bodies are intentionally not rendered.
  }
  return new AppApiError(
    'http_error',
    `The local backend returned status ${response.status}.`,
    response.status,
  )
}

const FRIENDLY: Record<string, string> = {
  network_error:
    'The local backend is unavailable. Your history is still safe.',
  request_aborted: 'The request was cancelled.',
  ollama_unavailable: 'Ollama is unavailable. You can still read your history.',
  ollama_timeout: 'The local model took too long to respond on this hardware.',
  ollama_model_not_configured:
    'Choose an installed Ollama model in backend settings.',
  ollama_model_not_installed: 'The configured model is not installed.',
  conversation_busy: 'This conversation is busy. Wait a moment and try again.',
  conversation_archived: 'Archived conversations are read-only.',
  conversation_inactive: 'This conversation is inactive and cannot generate.',
  message_edit_requires_truncation:
    'Editing this message requires removing everything that follows it.',
  message_delete_requires_truncation:
    'Deleting this message requires removing everything that follows it.',
  duplicate_client_message: 'This message was already accepted.',
}

export function friendlyError(error: unknown): string {
  if (error instanceof AppApiError) return FRIENDLY[error.code] ?? error.message
  return 'Something unexpected happened in the local application.'
}
