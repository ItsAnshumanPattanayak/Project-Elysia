import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const conversation = {
  id: 1,
  title: 'A Quiet Evening',
  character: { id: 1, slug: 'zara-mirza', display_name: 'Zara' },
  roleplay_user: { id: 1, roleplay_name: 'Anshuman' },
  current_scene: 'Rain against the windows',
  relationship_stage: 'committed',
  is_active: true,
  is_archived: false,
  message_count: 2,
  turn_count: 1,
  created_at: '2026-08-03T10:00:00Z',
  updated_at: '2026-08-03T10:01:00Z',
  last_message_at: '2026-08-03T10:01:00Z',
  relationship_state: {
    attraction: 70,
    trust: 75,
    affection: 72,
    respect: 80,
    comfort: 70,
    jealousy: 20,
    anger: 0,
    mood: 'affectionate',
    relationship_stage: 'committed',
    turn_count: 1,
  },
  recent_messages: [],
}
const userMessage = {
  id: 1,
  conversation_id: 1,
  sender: 'user',
  raw_content: 'I had a long day.',
  narration: null,
  dialogue: null,
  emotion: null,
  message_metadata: {},
  sequence_number: 1,
  is_edited: true,
  created_at: '2026-08-03T10:00:00Z',
  edited_at: '2026-08-03T10:00:30Z',
}
const characterMessage = {
  id: 2,
  conversation_id: 1,
  sender: 'character',
  raw_content: '*Zara looks up.* Sit with me.',
  narration: 'Zara looks up from her book.',
  dialogue: 'Sit with me. You do not have to carry the day alone.',
  emotion: 'concerned',
  message_metadata: { selected_memory_ids: [4] },
  sequence_number: 2,
  is_edited: false,
  created_at: '2026-08-03T10:01:00Z',
  edited_at: null,
}
const relationship = {
  conversation_id: 1,
  attraction: 70,
  trust: 75,
  affection: 72,
  respect: 80,
  comfort: 70,
  jealousy: 20,
  anger: 0,
  mood: 'affectionate',
  relationship_stage: 'committed',
  turn_count: 1,
  locked_values: {},
  baseline_values: {},
}
const health = {
  status: 'healthy',
  application: 'Project Elysia',
  version: '0.5.0',
  database: 'connected',
  environment: 'test',
}
const ai = {
  provider: 'ollama',
  available: true,
  state: 'ready',
  version: '0.32.0',
  configured_model: 'llama3.1:latest',
  model_ready: true,
  base_url: 'local',
  error_code: null,
  message: 'Ready.',
}

function json(value: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(value), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}
function mockBackend(options: { empty?: boolean; archived?: boolean } = {}) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
    const url = String(input)
    if (url.endsWith('/health')) return json(health)
    if (url.includes('/api/ai/status')) return json(ai)
    if (url.includes('/api/characters'))
      return json([
        {
          slug: 'zara-mirza',
          name: 'Zara Mirza',
          display_name: 'Zara',
          adult: true,
          profession: 'CEO',
          archetype: 'Romantic partner',
          description: 'Composed',
        },
      ])
    if (/\/api\/conversations\?/.test(url))
      return json({
        items: options.empty
          ? []
          : [{ ...conversation, is_archived: options.archived ?? false }],
        total: options.empty ? 0 : 1,
        limit: 100,
        offset: 0,
        has_more: false,
      })
    if (url.endsWith('/api/conversations/1/relationship'))
      return json(relationship)
    if (url.includes('/api/conversations/1/memories'))
      return json({ items: [], total: 3, limit: 1, offset: 0, has_more: true })
    if (
      url.includes('/api/conversations/1/messages') &&
      (!init?.method || init.method === 'GET')
    )
      return json({
        items: [userMessage, characterMessage],
        total: 2,
        limit: 50,
        offset: 0,
        has_more: false,
      })
    if (url.endsWith('/api/conversations/1'))
      return json({ ...conversation, is_archived: options.archived ?? false })
    return json(
      {
        error: {
          code: 'not_found',
          message: 'Not found',
          retryable: false,
          details: {},
        },
      },
      404,
    )
  })
}
function renderApp(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('Project Elysia chat MVP', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })
  it('shows polished empty state and create control', async () => {
    mockBackend({ empty: true })
    renderApp()
    expect(await screen.findByText('Your conversations,')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Begin a conversation' }),
    ).toBeEnabled()
  })
  it('redirects home to the latest conversation', async () => {
    mockBackend()
    renderApp()
    expect(await screen.findByText(/carry the day alone/)).toBeInTheDocument()
  })
  it('renders conversation sidebar and active item', async () => {
    mockBackend()
    renderApp('/chat/1')
    const link = await screen.findByRole('link', { name: /A Quiet Evening/ })
    expect(link).toHaveClass('active')
  })
  it('renders user, narration, dialogue, emotion and edited state', async () => {
    mockBackend()
    renderApp('/chat/1')
    expect(await screen.findByText('I had a long day.')).toBeInTheDocument()
    expect(screen.getByText('Zara looks up from her book.')).toBeInTheDocument()
    expect(screen.getByText(/carry the day alone/)).toBeInTheDocument()
    expect(screen.getByText('concerned')).toBeInTheDocument()
    expect(screen.getByText('edited')).toBeInTheDocument()
  })
  it('renders relationship and memory summaries', async () => {
    mockBackend()
    renderApp('/chat/1')
    expect(await screen.findByText('affectionate')).toBeInTheDocument()
    expect(screen.getByText('3 active recollections')).toBeInTheDocument()
    expect(
      screen.getByText('1 recalled for the latest response'),
    ).toBeInTheDocument()
  })
  it('disables composer for archived conversation', async () => {
    mockBackend({ archived: true })
    renderApp('/chat/1')
    expect(await screen.findByLabelText('Message Zara')).toBeDisabled()
    expect(
      screen.getByPlaceholderText('This conversation is read-only'),
    ).toBeInTheDocument()
  })
  it('rejects empty send and supports Shift+Enter', async () => {
    mockBackend()
    renderApp('/chat/1')
    const composer = await screen.findByLabelText('Message Zara')
    const send = screen.getByRole('button', { name: 'Send message' })
    expect(send).toBeDisabled()
    await userEvent.type(composer, 'Hello{shift>}{enter}{/shift}Zara')
    expect(composer).toHaveValue('Hello\nZara')
    expect(send).toBeEnabled()
  })
  it('opens create dialog with accessible name and closes on Escape', async () => {
    mockBackend({ empty: true })
    renderApp()
    await userEvent.click(
      await screen.findByRole('button', { name: 'Begin a conversation' }),
    )
    expect(
      await screen.findByRole('dialog', { name: 'Begin a new conversation' }),
    ).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
  it('opens delete confirmation with safe default', async () => {
    mockBackend()
    renderApp('/chat/1')
    await userEvent.click(
      (
        await screen.findAllByRole('button', { name: 'Delete conversation' })
      )[0],
    )
    expect(
      screen.getByRole('dialog', { name: 'Delete this conversation?' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
  })
  it('opens and closes mobile sidebar', async () => {
    mockBackend()
    renderApp('/chat/1')
    const open = await screen.findByRole('button', {
      name: 'Open conversations',
    })
    await userEvent.click(open)
    const sidebar = screen.getByLabelText('Conversations')
    expect(sidebar).toHaveClass('open')
    await userEvent.click(
      within(sidebar).getByRole('button', { name: 'Close conversations' }),
    )
    expect(sidebar).not.toHaveClass('open')
  })
  it('shows invalid conversation safely', async () => {
    mockBackend()
    renderApp('/chat/not-a-number')
    expect(
      await screen.findByText('This conversation address is invalid.'),
    ).toBeInTheDocument()
  })
  it('keeps backend status separate from model guidance', async () => {
    mockBackend()
    renderApp('/chat/1')
    const status = await screen.findByLabelText('Local system status')
    expect(status).toHaveTextContent('Local services')
    await userEvent.click(status)
    expect(
      screen.getByText('Model ready · generation may be slow'),
    ).toBeInTheDocument()
  })
  it('renders 404 route', async () => {
    mockBackend({ empty: true })
    renderApp('/missing')
    expect(
      await screen.findByText('This page is not part of Elysia.'),
    ).toBeInTheDocument()
  })
  it('refreshes a conversation', async () => {
    const mock = mockBackend()
    renderApp('/chat/1')
    await userEvent.click(
      await screen.findByRole('button', { name: 'Refresh conversation' }),
    )
    await waitFor(() =>
      expect(
        mock.mock.calls.filter(([url]) =>
          String(url).endsWith('/api/conversations/1'),
        ).length,
      ).toBeGreaterThan(1),
    )
  })
})
