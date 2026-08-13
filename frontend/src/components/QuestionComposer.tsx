import type { FormEvent, KeyboardEvent } from 'react'
import { ApiError } from './ApiError'

type QuestionComposerProps = {
  question: string
  error: string | null
  apiError: string | null
  isLoading: boolean
  onQuestionChange: (question: string) => void
  onSubmit: () => void
  onRetry: () => void
}

export function QuestionComposer({
  question,
  error,
  apiError,
  isLoading,
  onQuestionChange,
  onSubmit,
  onRetry,
}: QuestionComposerProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSubmit()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  return (
    <form className="composer" aria-label="Question composer" onSubmit={handleSubmit}>
      <label htmlFor="question">Your question</label>
      <textarea
        id="question"
        value={question}
        onChange={(event) => onQuestionChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="I want a novel that..."
        maxLength={500}
        aria-describedby={error ? (apiError ? 'api-error' : 'question-error') : 'question-count keyboard-hint'}
        aria-invalid={Boolean(error)}
        aria-keyshortcuts="Enter"
        disabled={isLoading}
        rows={3}
      />
      <div className="composer-footer">
        <span id="question-count">{question.length.toLocaleString()} / 500</span>
        <button className="send-button" type="submit" disabled={isLoading || !question}>
          <span>{isLoading ? 'Searching' : 'Ask librarian'}</span>
          <span className="send-icon" aria-hidden="true">↗</span>
        </button>
      </div>
      {!error && <span className="sr-only" id="keyboard-hint">Press Enter to send. Press Shift and Enter for a new line.</span>}
      {error && !apiError && <p className="error" id="question-error" role="alert">{error}</p>}
      {apiError && <ApiError message={apiError} isLoading={isLoading} onRetry={onRetry} />}
    </form>
  )
}