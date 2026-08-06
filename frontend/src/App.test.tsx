import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

const server = setupServer(
  http.post('http://127.0.0.1:8000/chat', () => HttpResponse.json({
    recommendation: { title: 'Dune', author: 'Frank Herbert', rationale: 'Its politics and world-building fit.' },
    summary: 'A complete local summary.',
  })),
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

it('submits a question and renders the recommendation and summary', async () => {
  const user = userEvent.setup()
  render(<App />)

  await user.type(screen.getByLabelText('Your question'), 'A science-fiction novel about politics')
  await user.click(screen.getByRole('button', { name: /ask librarian/i }))

  expect(await screen.findByRole('heading', { name: 'Dune' })).toBeVisible()
  expect(screen.getByText('Frank Herbert')).toBeVisible()
  expect(screen.getByText('A complete local summary.')).toBeVisible()
})

it('shows validation feedback without sending an empty question', async () => {
  const user = userEvent.setup()
  render(<App />)

  await user.type(screen.getByLabelText('Your question'), ' ')
  await user.click(screen.getByRole('button', { name: /ask librarian/i }))

  expect(screen.getByRole('alert')).toHaveTextContent('Ask a question')
})