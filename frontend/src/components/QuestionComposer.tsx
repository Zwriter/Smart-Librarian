import { useId, useState, type FormEvent, type KeyboardEvent } from 'react'
import { ApiError } from './ApiError'

const COMMANDS = [
  { name: 'query', description: 'Search the indexed catalogue' },
  { name: 'search', description: 'Search Google Books' },
  { name: 'year', description: 'Show the publication year' },
  { name: 'author', description: 'Show the author' },
  { name: 'language', description: 'Show the language' },
  { name: 'resume', description: 'Show the book resume' },
  { name: 'description', description: 'Show the book description' },
  { name: 'get', description: 'Return the book details' },
] as const

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
  const commandListId = useId()
  const [highlightedCommand, setHighlightedCommand] = useState(0)

  const commandMatch = question.match(/^\/([^\s]*)$/)
  const commandQuery = commandMatch?.[1].toLowerCase() ?? ''
  const commandSuggestions = commandMatch
    ? COMMANDS.filter(({ name }) => name.startsWith(commandQuery))
    : []
  const showCommandHints = commandSuggestions.length > 0

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSubmit()
  }

  function selectCommand(commandName: string) {
    onQuestionChange(`/${commandName} `)
    setHighlightedCommand(0)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (showCommandHints) {
      if (event.key === 'ArrowDown') {
        event.preventDefault()
        setHighlightedCommand((current) => (current + 1) % commandSuggestions.length)
        return
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault()
        setHighlightedCommand((current) => (current - 1 + commandSuggestions.length) % commandSuggestions.length)
        return
      }
      if ((event.key === 'Enter' || event.key === 'Tab') && !event.shiftKey) {
        event.preventDefault()
        selectCommand(commandSuggestions[highlightedCommand].name)
        return
      }
      if (event.key === 'Escape') {
        event.preventDefault()
        onQuestionChange('')
        return
      }
    }
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
        aria-controls={showCommandHints ? commandListId : undefined}
        aria-expanded={showCommandHints}
        aria-autocomplete="list"
      />
      {showCommandHints && (
        <div className="command-hints" id={commandListId} role="listbox" aria-label="Available commands">
          <span className="command-hints-label">Commands</span>
          {commandSuggestions.map((command, index) => (
            <button
              className={`command-hint${index === highlightedCommand ? ' is-highlighted' : ''}`}
              key={command.name}
              type="button"
              role="option"
              aria-selected={index === highlightedCommand}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => selectCommand(command.name)}
            >
              <strong>/{command.name}</strong>
              <span>{command.description}</span>
            </button>
          ))}
        </div>
      )}
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