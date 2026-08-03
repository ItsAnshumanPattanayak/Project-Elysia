import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import type { AIState, AIStatus } from './types/system'

const health = {
  status: 'healthy',
  application: 'Project Elysia',
  version: '0.2.0',
  database: 'connected',
  environment: 'test',
}

function aiStatus(state: AIState): AIStatus {
  return {
    provider: 'ollama',
    available: state !== 'unavailable',
    state,
    version: state === 'unavailable' ? null : '0.test',
    configured_model:
      state === 'model_not_configured' ? null : 'llama3.1:latest',
    model_ready: state === 'ready',
    base_url: 'http://127.0.0.1:11434',
    error_code: state === 'ready' ? null : `ollama_${state}`,
    message: state === 'ready' ? 'Ready locally.' : 'Not ready locally.',
  }
}

function mockServices(state: AIState = 'ready') {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = String(input)
    const payload = url.includes('/api/ai/status') ? aiStatus(state) : health
    return Promise.resolve(
      new Response(JSON.stringify(payload), { status: 200 }),
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

describe('Project Elysia Batch 2 foundation', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('renders the title and loading state', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      () => new Promise(() => {}),
    )
    renderApp()
    expect(screen.getByText('Project Elysia')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent(
      'Checking your local services',
    )
  })

  it('shows backend, database, and ready Ollama state', async () => {
    mockServices('ready')
    renderApp()
    expect(await screen.findByText('Backend connected')).toBeInTheDocument()
    expect(screen.getByText('Database: connected')).toBeInTheDocument()
    expect(screen.getByText('Ollama ready')).toBeInTheDocument()
    expect(screen.getByText(/llama3.1:latest/)).toBeInTheDocument()
  })

  it.each([
    ['unavailable', 'Ollama unavailable'],
    ['model_not_configured', 'Model not configured'],
    ['model_not_installed', 'Configured model missing'],
  ] as const)('shows %s independently', async (state, label) => {
    mockServices(state)
    renderApp()
    expect(await screen.findByText(label)).toBeInTheDocument()
    expect(screen.getByText('Backend connected')).toBeInTheDocument()
  })

  it('refreshes AI status without losing backend state', async () => {
    const fetchMock = mockServices('ready')
    renderApp()
    const refresh = await screen.findByRole('button', {
      name: 'Refresh AI status',
    })
    fireEvent.click(refresh)
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([url]) =>
          String(url).includes('refresh=true'),
        ),
      ).toBe(true),
    )
    expect(screen.getByText('Backend connected')).toBeInTheDocument()
  })

  it('keeps backend failure distinct and retries', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockRejectedValueOnce(new TypeError('offline'))
      .mockImplementation((input) => {
        const payload = String(input).includes('/api/ai/status')
          ? aiStatus('ready')
          : health
        return Promise.resolve(
          new Response(JSON.stringify(payload), { status: 200 }),
        )
      })
    renderApp()
    const retry = await screen.findByRole('button', {
      name: 'Retry connection',
    })
    expect(screen.getByText('Backend unavailable')).toBeInTheDocument()
    fireEvent.click(retry)
    expect(await screen.findByText('Ollama ready')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalled()
  })

  it('renders the not-found route', () => {
    mockServices()
    renderApp('/missing')
    expect(
      screen.getByText('This page is not part of Elysia.'),
    ).toBeInTheDocument()
  })

  it('catches render errors', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    function Broken(): never {
      throw new Error('broken')
    }
    render(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })
})
