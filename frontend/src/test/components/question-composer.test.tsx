import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QuestionComposer } from '../../components/QuestionComposer'

function renderComposer(overrides: Partial<Parameters<typeof QuestionComposer>[0]> = {}) {
  const props = {
    question: 'A thoughtful question',
    error: null,
    apiError: null,
    isLoading: false,
    onQuestionChange: vi.fn(),
    onSubmit: vi.fn(),
    onRetry: vi.fn(),
    ...overrides,
  }

  return { ...render(<QuestionComposer {...props} />), props }
}

test('provides a semantic multiline composer and accessible send action', () => {
  const { props } = renderComposer()

  const form = screen.getByRole('form', { name: 'Question composer' })
  const textarea = screen.getByRole('textbox', { name: 'Your question' })

  expect(form).toContainElement(textarea)
  expect(textarea).toHaveAttribute('rows', '3')
  expect(screen.getByRole('button', { name: 'Ask librarian' })).toBeEnabled()
  expect(screen.getByText(/press enter to send/i)).toBeInTheDocument()

  fireEvent.change(textarea, { target: { value: 'First line\nSecond line' } })
  expect(props.onQuestionChange).toHaveBeenCalledWith('First line\nSecond line')
})

test('submits on Enter but leaves Shift+Enter available for a new line', () => {
  const { props } = renderComposer()
  const textarea = screen.getByRole('textbox', { name: 'Your question' })

  fireEvent.keyDown(textarea, { key: 'Shift', code: 'ShiftLeft', shiftKey: true })
  fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter', shiftKey: true })
  expect(props.onSubmit).not.toHaveBeenCalled()

  fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' })
  expect(props.onSubmit).toHaveBeenCalledOnce()
})

test('disables the textarea and all composer actions while loading', () => {
  renderComposer({ isLoading: true, apiError: 'The catalogue is unavailable.' })

  expect(screen.getByRole('textbox', { name: 'Your question' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Searching' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Retry request' })).toBeDisabled()
})

test('supports keyboard-only focus and submission', async () => {
  const user = userEvent.setup()
  const { props } = renderComposer()

  await user.tab()
  expect(screen.getByRole('textbox', { name: 'Your question' })).toHaveFocus()
  await user.tab()
  expect(screen.getByRole('button', { name: 'Ask librarian' })).toHaveFocus()
  await user.keyboard('{Enter}')

  expect(props.onSubmit).toHaveBeenCalledOnce()
})

test('shows available commands after typing a slash', () => {
  const { props } = renderComposer({ question: '/' })

  expect(screen.getByRole('listbox', { name: 'Available commands' })).toBeInTheDocument()
  expect(screen.getAllByRole('option')).toHaveLength(8)
  expect(screen.getByRole('option', { name: /\/resume.*show the book resume/i })).toBeInTheDocument()
  expect(props.onQuestionChange).not.toHaveBeenCalled()
})

test('filters and selects a command with the keyboard', () => {
  const { props } = renderComposer({ question: '/de' })
  const textarea = screen.getByRole('textbox', { name: 'Your question' })

  expect(screen.getAllByRole('option')).toHaveLength(1)
  fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' })

  expect(props.onQuestionChange).toHaveBeenCalledWith('/description ')
})

test('selects a command with a pointer click', () => {
  const { props } = renderComposer({ question: '/' })

  fireEvent.click(screen.getByRole('option', { name: /\/get.*return the book details/i }))

  expect(props.onQuestionChange).toHaveBeenCalledWith('/get ')
})