import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createConversation,
  deleteConversation,
  listConversations,
  updateConversation,
} from './conversations'
import { AppApiError } from './errors'
import { listMessages } from './messages'
import {
  getRelationship,
  listRelationshipEvents,
  recalculateRelationship,
  updateRelationship,
} from './relationships'
import {
  archiveMemory,
  createMemory,
  listMemories,
  rebuildMemories,
  searchMemoryPreview,
} from './memories'
import { getSettings, resetSettings, updateSettings } from './settings'
import { requestJson, requestVoid } from './client'

const summary = {
  id: 1,
  title: 'Chat',
  character: { id: 1, slug: 'zara-mirza', display_name: 'Zara' },
  roleplay_user: { id: 1, roleplay_name: 'Anshuman' },
  current_scene: '',
  relationship_stage: 'committed',
  is_active: true,
  is_archived: false,
  message_count: 0,
  turn_count: 0,
  created_at: 'x',
  updated_at: 'x',
  last_message_at: null,
  relationship_state: {},
  recent_messages: [],
}
const response = (value: unknown, status = 200) =>
  Promise.resolve(
    new Response(status === 204 ? null : JSON.stringify(value), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )

describe('typed API layer', () => {
  beforeEach(() => vi.restoreAllMocks())
  it('parses conversation pagination', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      response({
        items: [summary],
        total: 1,
        limit: 20,
        offset: 0,
        has_more: false,
      }),
    )
    expect((await listConversations()).total).toBe(1)
  })
  it('creates a conversation with POST JSON', async () => {
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(() => response(summary))
    await createConversation({
      character_slug: 'zara-mirza',
      roleplay_user_slug: 'anshuman',
    })
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/conversations'),
      expect.objectContaining({ method: 'POST' }),
    )
  })
  it('updates a conversation', async () => {
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(() => response(summary))
    await updateConversation(1, { title: 'New' })
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/1'),
      expect.objectContaining({ method: 'PATCH' }),
    )
  })
  it('accepts delete 204', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => response(null, 204))
    await expect(deleteConversation(1)).resolves.toBeUndefined()
  })
  it('rejects non-204 for void requests', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      response({ ok: true }),
    )
    await expect(requestVoid('/x')).rejects.toMatchObject({
      code: 'invalid_response',
    })
  })
  it('parses message pagination', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      response({ items: [], total: 0, limit: 50, offset: 0, has_more: false }),
    )
    expect((await listMessages(1)).items).toEqual([])
  })
  it('parses relationship response', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      response({ conversation_id: 1, mood: 'neutral', trust: 50 }),
    )
    expect((await getRelationship(1)).mood).toBe('neutral')
  })
  it('parses memory summary total', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      response({ items: [], total: 4, limit: 1, offset: 0, has_more: true }),
    )
    expect((await listMemories(1)).total).toBe(4)
  })
  it('normalizes backend error envelope', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      response(
        {
          error: {
            code: 'conversation_busy',
            message: 'Busy',
            retryable: true,
            details: {},
          },
        },
        409,
      ),
    )
    await expect(listConversations()).rejects.toMatchObject({
      code: 'conversation_busy',
      status: 409,
      retryable: true,
    })
  })
  it('normalizes non-JSON errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('<html>bad</html>', { status: 500 }),
    )
    await expect(listConversations()).rejects.toMatchObject({
      code: 'http_error',
    })
  })
  it('normalizes network failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'))
    await expect(listConversations()).rejects.toMatchObject({
      code: 'network_error',
    })
  })
  it('normalizes AbortError separately', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(
      new DOMException('aborted', 'AbortError'),
    )
    await expect(listConversations()).rejects.toMatchObject({
      code: 'request_aborted',
    })
  })
  it('rejects empty JSON response', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => response(null, 204))
    await expect(
      requestJson('/x', (_value): _value is unknown => true),
    ).rejects.toMatchObject({ code: 'empty_response' })
  })
  it('passes an AbortSignal', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      response({
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
        has_more: false,
      }),
    )
    const controller = new AbortController()
    await listConversations({}, controller.signal)
    expect(fetch.mock.calls[0][1]).toMatchObject({ signal: controller.signal })
  })
  it('uses only the configured centralized base URL', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      response({
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
        has_more: false,
      }),
    )
    await listConversations()
    expect(String(fetch.mock.calls[0][0])).toMatch(
      /^http:\/\/127\.0\.0\.1:8000\/api\//,
    )
  })
  it('rejects invalid response shapes', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      response({ unexpected: true }),
    )
    await expect(listConversations()).rejects.toBeInstanceOf(AppApiError)
  })
  it('sends relationship filters and parses pagination', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      response({
        items: [],
        total: 0,
        limit: 25,
        offset: 0,
        has_more: false,
      }),
    )
    await listRelationshipEvents(4, {
      source: 'manual',
      reverted: false,
      oldestFirst: true,
    })
    expect(String(fetch.mock.calls[0][0])).toContain('source=manual')
    expect(String(fetch.mock.calls[0][0])).toContain('reverted=false')
  })
  it('updates and recalculates relationship safely', async () => {
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => response({ event_id: 9 }))
      .mockImplementationOnce(() =>
        response({
          before: { conversation_id: 1, mood: 'neutral', trust: 50 },
          after: { conversation_id: 1, mood: 'happy', trust: 52 },
          warnings: [],
        }),
      )
    await updateRelationship(1, { trust: 52, reason: 'Test' })
    expect(fetch.mock.calls[0][1]).toMatchObject({ method: 'PATCH' })
    expect((await recalculateRelationship(1)).after.mood).toBe('happy')
  })
  it('sends all safe memory filters', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      response({
        items: [],
        total: 0,
        limit: 25,
        offset: 0,
        has_more: false,
      }),
    )
    await listMemories(2, {
      status: '',
      type: 'user_fact',
      pinned: true,
      locked: false,
      sensitive: true,
      query: 'local',
      limit: 25,
    })
    const url = String(fetch.mock.calls[0][0])
    expect(url).not.toContain('status=')
    expect(url).toContain('locked=false')
    expect(url).toContain('query=local')
  })
  it('creates, previews, rebuilds, and archives memories', async () => {
    const memory = { id: 3, content: 'Local fact' }
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => response(memory))
      .mockImplementationOnce(() =>
        response({ items: [], total_characters: 0 }),
      )
      .mockImplementationOnce(() =>
        response({ before: {}, after: {}, warnings: [] }),
      )
      .mockImplementationOnce(() => response(null, 204))
    await createMemory(1, {
      content: 'Local fact',
      memory_type: 'user_fact',
    })
    await searchMemoryPreview(1, { query: 'fact' })
    await rebuildMemories(1)
    await archiveMemory(1, 3)
    expect(fetch.mock.calls.map((call) => call[1]?.method)).toEqual([
      'POST',
      'POST',
      'POST',
      'DELETE',
    ])
  })
  it('loads, saves, and resets safe settings', async () => {
    const payload = {
      schema_version: 1,
      items: [
        {
          key: 'temperature',
          value: 0.8,
          category: 'ai',
          is_default: true,
          restart_required: false,
        },
      ],
    }
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(() => response(payload))
    expect((await getSettings()).items[0].key).toBe('temperature')
    await updateSettings({ temperature: 1 })
    await resetSettings({ category: 'ai' })
    expect(fetch.mock.calls.map((call) => call[1]?.method)).toEqual([
      undefined,
      'PATCH',
      'POST',
    ])
  })
})
