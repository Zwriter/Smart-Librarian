import { fireEvent, render, screen } from '@testing-library/react'
import { ConversationList } from '../../components/ConversationList'
import { MessageBubble } from '../../components/MessageBubble'

function setScrollMetrics(element: HTMLElement, values: { scrollHeight: number; scrollTop: number; clientHeight: number }) {
  Object.defineProperties(element, {
    scrollHeight: { configurable: true, value: values.scrollHeight },
    scrollTop: { configurable: true, writable: true, value: values.scrollTop },
    clientHeight: { configurable: true, value: values.clientHeight },
  })
}

test('labels each message by speaker and preserves assistant whitespace', () => {
  render(
    <div>
      <MessageBubble message={{ role: 'user', content: 'Find a quiet mystery' }} />
      <MessageBubble message={{ role: 'assistant', content: 'Start here.\n\nThe setting stays with you.' }} />
    </div>,
  )

  expect(screen.getByRole('article', { name: 'You message' })).toHaveClass('user')
  const assistantMessage = screen.getByRole('article', { name: 'Librarian message' })
  expect(assistantMessage).toHaveClass('assistant')
  expect(assistantMessage.querySelector('p')?.textContent).toBe('Start here.\n\nThe setting stays with you.')
})

test('does not scroll away from a reader who is reviewing older messages', () => {
  const scrollTo = vi.fn()
  const { rerender } = render(
    <ConversationList messages={[{ role: 'user', content: 'First question' }]} />,
  )
  const conversation = screen.getByRole('region', { name: 'Conversation history' })
  Object.defineProperty(conversation, 'scrollTo', { configurable: true, value: scrollTo })
  setScrollMetrics(conversation, { scrollHeight: 1_000, scrollTop: 100, clientHeight: 300 })
  fireEvent.scroll(conversation)

  rerender(
    <ConversationList
      messages={[
        { role: 'user', content: 'First question' },
        { role: 'assistant', content: 'A considered answer' },
      ]}
    />,
  )

  expect(scrollTo).not.toHaveBeenCalled()
})

test('follows a new message when the reader is already near the latest message', () => {
  const scrollTo = vi.fn()
  const { rerender } = render(
    <ConversationList messages={[{ role: 'user', content: 'First question' }]} />,
  )
  const conversation = screen.getByRole('region', { name: 'Conversation history' })
  Object.defineProperty(conversation, 'scrollTo', { configurable: true, value: scrollTo })
  setScrollMetrics(conversation, { scrollHeight: 1_000, scrollTop: 700, clientHeight: 300 })
  fireEvent.scroll(conversation)
  scrollTo.mockClear()

  rerender(
    <ConversationList
      messages={[
        { role: 'user', content: 'First question' },
        { role: 'assistant', content: 'A considered answer' },
      ]}
    />,
  )

  expect(scrollTo).toHaveBeenCalledWith({ top: 1_000, behavior: 'smooth' })
})