import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'

const health = {
  status: 'healthy',
  application: 'Project Elysia',
  version: '0.1.0',
  database: 'connected',
  environment: 'test',
}

function renderApp(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('Project Elysia foundation', () => {
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

  it('shows successful backend and database health', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(health), { status: 200 }),
    )
    renderApp()
    expect(await screen.findByText('Backend connected')).toBeInTheDocument()
    expect(screen.getByText('Database: connected')).toBeInTheDocument()
    expect(screen.getByText('Not configured yet')).toBeInTheDocument()
  })

  it('shows unavailable state and retries', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockRejectedValueOnce(new TypeError('offline'))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(health), { status: 200 }),
      )
    renderApp()
    const retry = await screen.findByRole('button', {
      name: 'Retry connection',
    })
    fireEvent.click(retry)
    await waitFor(() =>
      expect(screen.getByText('Backend connected')).toBeInTheDocument(),
    )
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('renders the not-found route', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      () => new Promise(() => {}),
    )
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
