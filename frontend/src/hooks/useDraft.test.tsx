import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useDraft } from './useDraft'

function Harness({ id }: { id: number }) {
  const { draft, setDraft, clear } = useDraft(id)
  return (
    <>
      <label>
        Draft
        <input
          aria-label="Draft"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
      </label>
      <button onClick={clear}>Clear</button>
    </>
  )
}
describe('conversation drafts', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })
  afterEach(() => vi.useRealTimers())
  it('saves a bounded per-conversation draft', async () => {
    render(<Harness id={4} />)
    fireEvent.change(screen.getByLabelText('Draft'), {
      target: { value: 'Private draft' },
    })
    await act(async () => vi.advanceTimersByTime(200))
    expect(localStorage.getItem('elysia:draft:4')).toBe('Private draft')
  })
  it('restores a draft', () => {
    localStorage.setItem('elysia:draft:7', 'Restored')
    render(<Harness id={7} />)
    expect(screen.getByLabelText('Draft')).toHaveValue('Restored')
  })
  it('switches drafts by conversation', () => {
    localStorage.setItem('elysia:draft:1', 'One')
    localStorage.setItem('elysia:draft:2', 'Two')
    const view = render(<Harness id={1} />)
    expect(screen.getByLabelText('Draft')).toHaveValue('One')
    view.rerender(<Harness id={2} />)
    expect(screen.getByLabelText('Draft')).toHaveValue('Two')
  })
  it('clears storage after acceptance', async () => {
    localStorage.setItem('elysia:draft:1', 'One')
    render(<Harness id={1} />)
    await userEvent.click(screen.getByRole('button', { name: 'Clear' }))
    expect(screen.getByLabelText('Draft')).toHaveValue('')
    expect(localStorage.getItem('elysia:draft:1')).toBeNull()
  })
  it('handles unavailable storage', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(() => render(<Harness id={1} />)).not.toThrow()
  })
  it('limits restored draft length', () => {
    localStorage.setItem('elysia:draft:1', 'a'.repeat(11_000))
    render(<Harness id={1} />)
    expect(
      (screen.getByLabelText('Draft') as HTMLInputElement).value,
    ).toHaveLength(10_000)
  })
})
