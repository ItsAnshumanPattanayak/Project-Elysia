import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

interface Toast {
  id: number
  message: string
  critical: boolean
}
const ToastContext = createContext<
  (message: string, critical?: boolean) => void
>(() => undefined)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const notify = useCallback((message: string, critical = false) => {
    const id = Date.now() + Math.random()
    setToasts((current) => [...current.slice(-2), { id, message, critical }])
    if (!critical)
      window.setTimeout(
        () => setToasts((current) => current.filter((item) => item.id !== id)),
        3500,
      )
  }, [])
  const value = useMemo(() => notify, [notify])
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="toast-region"
        role="status"
        aria-live="polite"
        aria-label="Notifications"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`toast ${toast.critical ? 'critical' : ''}`}
          >
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
// The provider and its consumer hook intentionally share this tiny context module.
// eslint-disable-next-line react-refresh/only-export-components
export const useToast = () => useContext(ToastContext)
