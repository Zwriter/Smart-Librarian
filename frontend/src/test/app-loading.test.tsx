import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import App from '../App'
import { createChatServer } from './appTestServer'

const chatServer = createChatServer()

beforeAll(() => chatServer.listen())
afterEach(() => chatServer.resetHandlers())
afterAll(() => chatServer.close())

test('shows the loading state while the librarian is answering', async () => {
  let releaseResponse!: () => void
  const responseReleased = new Promise<void>((resolve) => {
    releaseResponse = resolve
  })
  chatServer.use(http.post('http://127.0.0.1:8000/chat', async () => {
    await responseReleased
    return HttpResponse.json({
      recommendation: { title: 'Dune', author: 'Frank Herbert', rationale: 'A match.' },
      summary: 'A complete summary.',
    })
  }))

  const user = userEvent.setup()
  render(<App />)

  await user.type(screen.getByLabelText('Your question'), 'A science-fiction novel')
  await user.click(screen.getByRole('button', { name: /ask librarian/i }))

  expect(screen.getByRole('status')).toHaveTextContent('Searching the stacks')
  expect(screen.getByRole('button', { name: /searching/i })).toBeDisabled()
  releaseResponse()
  expect(await screen.findByRole('heading', { name: 'Dune' })).toBeVisible()
})
