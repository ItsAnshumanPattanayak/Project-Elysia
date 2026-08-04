import { Modal } from './Modal'

export function ConfirmationDialog({
  title,
  consequence,
  confirmLabel = 'Continue',
  destructive = false,
  onConfirm,
  onCancel,
}: {
  title: string
  consequence: string
  confirmLabel?: string
  destructive?: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <Modal title={title} onClose={onCancel}>
      <p className="modal-copy">{consequence}</p>
      <div className="modal-actions">
        <button
          type="button"
          className="button secondary"
          data-autofocus
          onClick={onCancel}
        >
          Cancel
        </button>
        <button
          type="button"
          className={`button ${destructive ? 'danger' : ''}`}
          onClick={onConfirm}
        >
          {confirmLabel}
        </button>
      </div>
    </Modal>
  )
}
