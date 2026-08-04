import { useEffect, useState } from 'react'
import { useHistory } from 'react-router-dom'
import { listCharacters } from '../../api/conversations'
import { friendlyError } from '../../api/errors'
import { useApp } from '../../state/AppContext'
import type { CharacterSummary } from '../../types/conversation'
import { Modal } from '../common/Modal'

export function NewConversationDialog() {
  const { newDialogOpen, setNewDialogOpen, create } = useApp()
  const [characters, setCharacters] = useState<CharacterSummary[]>([])
  const [character, setCharacter] = useState('zara-mirza')
  const [title, setTitle] = useState('')
  const [scene, setScene] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const history = useHistory()
  useEffect(() => {
    if (!newDialogOpen) return
    const controller = new AbortController()
    void listCharacters(controller.signal)
      .then((items) => {
        setCharacters(items)
        if (items.some((item) => item.slug === 'zara-mirza'))
          setCharacter('zara-mirza')
        else if (items[0]) setCharacter(items[0].slug)
      })
      .catch((reason) => setError(friendlyError(reason)))
    return () => controller.abort()
  }, [newDialogOpen])
  if (!newDialogOpen) return null
  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!character) return setError('Choose a character.')
    setBusy(true)
    try {
      const item = await create({
        character_slug: character,
        roleplay_user_slug: 'anshuman',
        ...(title.trim() ? { title: title.trim() } : {}),
        current_scene: scene.trim(),
      })
      setNewDialogOpen(false)
      setTitle('')
      setScene('')
      history.push(`/chat/${item.id}`)
    } catch (reason) {
      setError(friendlyError(reason))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Modal
      title="Begin a new conversation"
      onClose={() => setNewDialogOpen(false)}
    >
      <form className="form-stack" onSubmit={(event) => void submit(event)}>
        <label>
          Character
          <select
            value={character}
            onChange={(event) => setCharacter(event.target.value)}
            disabled={busy}
          >
            {characters.map((item) => (
              <option key={item.slug} value={item.slug}>
                {item.display_name} · {item.archetype}
              </option>
            ))}
          </select>
        </label>
        <label>
          Roleplay profile
          <input value="Anshuman" disabled aria-describedby="profile-note" />
        </label>
        <small id="profile-note">Fictional local profile</small>
        <label>
          Title <span>optional</span>
          <input
            maxLength={250}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <label>
          Opening scene <span>optional</span>
          <textarea
            maxLength={2000}
            rows={3}
            value={scene}
            onChange={(event) => setScene(event.target.value)}
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="modal-actions">
          <button
            type="button"
            className="button secondary"
            onClick={() => setNewDialogOpen(false)}
          >
            Cancel
          </button>
          <button className="button" disabled={busy || !character}>
            {busy ? 'Creating…' : 'Create conversation'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
