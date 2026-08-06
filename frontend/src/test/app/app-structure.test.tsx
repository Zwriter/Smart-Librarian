import { render, screen } from '@testing-library/react'
import App from '../../App'

test('renders the primary librarian workflow and empty state', () => {
  render(<App />)

  expect(screen.getByRole('banner')).toHaveTextContent('Smart Librarian')
  expect(screen.getByRole('heading', { name: /find your next good book/i })).toBeVisible()
  expect(screen.getByRole('button', { name: 'Clear shelf' })).toBeDisabled()
  expect(screen.getByRole('region', { name: 'Conversation history' })).toBeVisible()
  expect(screen.getByRole('form', { name: 'Question composer' })).toBeVisible()
  expect(screen.getByText(/describe a mood/i)).toBeVisible()
  expect(screen.getByRole('complementary')).toHaveTextContent('Your recommendation will appear here')
})

