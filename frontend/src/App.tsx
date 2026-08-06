import { useChat } from './hooks/useChat'
import './App.css'

function App() {
  const chat = useChat()

  return (
    <div className="app-shell">
      <header className="site-header">
        <div>
          <p className="eyebrow">Smart Librarian</p>
          <h1>Find your next <em>good</em> book.</h1>
        </div>
        <button className="text-button" type="button" onClick={chat.clearConversation} disabled={!chat.messages.length && !chat.response}>
          Clear shelf
        </button>
      </header>

      <main className="library-layout">
        <section className="conversation-panel" aria-labelledby="conversation-heading">
          <div className="section-heading">
            <div>
              <p className="eyebrow">The reading room</p>
              <h2 id="conversation-heading">Tell me what you are looking for</h2>
            </div>
            <span className="message-count">{chat.messages.length} / 20 notes</span>
          </div>

          <div className="conversation" aria-live="polite">
            {!chat.messages.length && !chat.isLoading && (
              <div className="empty-state">
                <span className="book-mark" aria-hidden="true">✦</span>
                <p>Describe a mood, a genre, or the last story you could not put down.</p>
                <span className="prompt-hint">Try “A mysterious story with an unforgettable setting.”</span>
              </div>
            )}
            {chat.messages.map((message, index) => (
              <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
                <span className="message-role">{message.role === 'user' ? 'You' : 'Librarian'}</span>
                <p>{message.content}</p>
              </article>
            ))}
            {chat.isLoading && <div className="loading" role="status">Searching the stacks<span>...</span></div>}
          </div>

          <form className="composer" onSubmit={(event) => { event.preventDefault(); void chat.submitQuestion() }}>
            <label htmlFor="question">Your question</label>
            <textarea
              id="question"
              value={chat.question}
              onChange={(event) => chat.setQuestion(event.target.value)}
              placeholder="I want a novel that..."
              maxLength={2000}
              aria-describedby={chat.error ? 'question-error' : 'question-count'}
              aria-invalid={Boolean(chat.error)}
              disabled={chat.isLoading}
              rows={3}
            />
            <div className="composer-footer">
              <span id="question-count">{chat.question.length.toLocaleString()} / 2,000</span>
              <button className="send-button" type="submit" disabled={chat.isLoading || !chat.question}>
                {chat.isLoading ? 'Searching' : 'Ask librarian'} <span aria-hidden="true">→</span>
              </button>
            </div>
            {chat.error && <p className="error" id="question-error" role="alert">{chat.error}</p>}
            {chat.apiError && (
              <button className="text-button" type="button" onClick={() => void chat.retry()} disabled={chat.isLoading}>
                Retry request
              </button>
            )}
          </form>
        </section>

        <aside className="result-panel" aria-labelledby="result-heading">
          <p className="eyebrow">From the catalogue</p>
          <h2 id="result-heading">{chat.response ? 'A considered recommendation' : 'Your recommendation will appear here'}</h2>
          {chat.response ? (
            <>
              <div className="recommendation">
                <p className="result-label">Recommended title</p>
                <h3>{chat.response.recommendation.title}</h3>
                <p className="author">{chat.response.recommendation.author}</p>
                <p className="rationale">{chat.response.recommendation.rationale}</p>
              </div>
              <div className="summary">
                <p className="result-label">The long view</p>
                <p>{chat.response.summary}</p>
              </div>
            </>
          ) : (
            <div className="result-placeholder"><span aria-hidden="true">“</span><p>The right book can change the shape of an evening.</p></div>
          )}
        </aside>
      </main>
      <footer>Recommendations are powered by your local book catalogue.</footer>
    </div>
  )
}

export default App
