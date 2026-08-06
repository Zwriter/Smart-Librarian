import { render, screen } from '@testing-library/react'
import { ApiError } from '../components/ApiError'
import { ConversationList } from '../components/ConversationList'
import { LoadingIndicator } from '../components/LoadingIndicator'

test('announces active requests accessibly', () => {
  render(<LoadingIndicator />)

  expect(screen.getByRole('status')).toHaveTextContent('Searching the stacks')
  expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite')
  expect(screen.getByRole('status')).toHaveAttribute('aria-atomic', 'true')
})

test('announces API errors and exposes a disabled-safe retry action', () => {
  const onRetry = vi.fn()
  const { rerender } = render(<ApiError message="The catalogue is unavailable." isLoading={false} onRetry={onRetry} />)

  expect(screen.getByRole('alert')).toHaveTextContent('The catalogue is unavailable.')
  screen.getByRole('button', { name: 'Retry request' }).click()
  expect(onRetry).toHaveBeenCalledOnce()

  rerender(<ApiError message="The catalogue is unavailable." isLoading onRetry={onRetry} />)
  expect(screen.getByRole('button', { name: 'Retry request' })).toBeDisabled()
})

test('reserves the loading indicator slot when no request is active', () => {
  const { rerender } = render(<ConversationList messages={[]} />)
  const conversation = screen.getByRole('region', { name: 'Conversation history' })

  expect(conversation.querySelector('.loading-slot')).toBeInTheDocument()
  expect(screen.queryByRole('status')).not.toBeInTheDocument()

  rerender(<ConversationList messages={[]} isLoading />)
  expect(screen.getByRole('status')).toBeVisible()
})