import { AppStatus } from '../components/AppStatus'

const capabilities = [
  ['Local API', 'FastAPI foundation ready'],
  ['Private storage', 'SQLite data stays on this device'],
  ['AI connection', 'Not configured yet'],
]

export function HomePage() {
  return (
    <main>
      <section className="hero">
        <div className="eyebrow">Local-first · Private by design</div>
        <h1>
          A quiet space for
          <br />
          <em>character stories.</em>
        </h1>
        <p className="lede">
          Project Elysia is the foundation for a personal AI character
          experience—built to remain yours, on your machine.
        </p>
        <AppStatus />
      </section>
      <section className="panel" aria-labelledby="foundation-heading">
        <div>
          <p className="overline">Current milestone</p>
          <h2 id="foundation-heading">The foundation is ready.</h2>
          <p>
            Data models, local storage, and service health are in place.
            Character chat and local AI generation arrive in later batches.
          </p>
        </div>
        <div className="capabilities">
          {capabilities.map(([title, detail], index) => (
            <article key={title}>
              <span>0{index + 1}</span>
              <div>
                <h3>{title}</h3>
                <p>{detail}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  )
}
