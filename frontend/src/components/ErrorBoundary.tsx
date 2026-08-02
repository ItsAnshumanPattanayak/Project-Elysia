import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}
interface State {
  failed: boolean
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }
  static getDerivedStateFromError(): State {
    return { failed: true }
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Application render failed', error, info)
  }
  render() {
    return this.state.failed ? (
      <main className="center">
        <h1>Something went wrong</h1>
        <p>Reload the local app to try again.</p>
      </main>
    ) : (
      this.props.children
    )
  }
}
