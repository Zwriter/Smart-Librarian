import { useChat } from './hooks/useChat'
import { ConversationList } from './components/ConversationList'
import { QuestionComposer } from './components/QuestionComposer'
import { RecommendationCard } from './components/RecommendationCard'
import { RecommendationOptions } from './components/RecommendationOptions'
import { BookSummary } from './components/BookSummary'

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
          <span className="action-icon" aria-hidden="true">×</span>{' '}
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

          <ConversationList messages={chat.messages} isLoading={chat.isLoading} />

          <QuestionComposer
            question={chat.question}
            error={chat.error}
            apiError={chat.apiError}
            isLoading={chat.isLoading}
            onQuestionChange={chat.setQuestion}
            onSubmit={() => void chat.submitQuestion()}
            onRetry={() => void chat.retry()}
          />
        </section>

        <aside className="result-panel" aria-labelledby="result-heading">
          {chat.response && (
            <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
              {chat.response.message ?? `Recommendation ready: ${chat.response.recommendation?.title}.`}
            </p>
          )}
          <p className="eyebrow">From the catalogue</p>
          <h2 id="result-heading">{chat.response?.recommendations ? 'A few paths from the catalogue' : chat.response?.message ? 'A note from the librarian' : chat.response ? 'A considered recommendation' : 'Your recommendation will appear here'}</h2>
          {chat.response?.message ? (
            <>
              {chat.response.recommendations && <RecommendationOptions recommendations={chat.response.recommendations} />}
              <div className="result-placeholder"><p>{chat.response.message}</p></div>
            </>
          ) : chat.response?.recommendation && chat.response.summary ? (
            <>
              <RecommendationCard recommendation={chat.response.recommendation} />
              <BookSummary summary={chat.response.summary} />
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
