import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <main className="chat-error">
      <p className="overline">404</p>
      <h1>This page is not part of Elysia.</h1>
      <Link className="button" to="/">
        Return home
      </Link>
    </main>
  )
}
