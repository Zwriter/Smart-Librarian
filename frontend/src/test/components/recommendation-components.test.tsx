import { render, screen, within } from '@testing-library/react'
import { BookSummary } from '../../components/BookSummary'
import { RecommendationCard } from '../../components/RecommendationCard'

test('renders long recommendation metadata without truncation', () => {
  const longRationale = 'A thoughtful match for the reader with a deliberately long explanation that can wrap at narrow widths without escaping its panel.'
  render(
    <RecommendationCard
      recommendation={{
        title: 'The Absolutely Remarkable Story With An Unusually Long Title',
        author: 'An Author With A Name That Needs Room To Wrap Gracefully',
        rationale: longRationale,
      }}
    />,
  )

  const card = screen.getByRole('region', { name: 'The Absolutely Remarkable Story With An Unusually Long Title' })
  expect(within(card).getByRole('heading')).toHaveTextContent('The Absolutely Remarkable Story With An Unusually Long Title')
  expect(within(card).getByText('An Author With A Name That Needs Room To Wrap Gracefully')).toBeVisible()
  expect(within(card).getByText(longRationale)).toBeVisible()
})

test('renders every summary paragraph and preserves line breaks within paragraphs', () => {
  render(<BookSummary summary={'First paragraph, kept complete.\nA second line.\n\nSecond paragraph, also complete.'} />)

  const summary = screen.getByRole('region', { name: 'The long view' })
  expect(within(summary).getAllByRole('paragraph')).toHaveLength(3)
  expect(within(summary).getByText(/First paragraph/)).toHaveTextContent('First paragraph, kept complete. A second line.')
  expect(within(summary).getByText('Second paragraph, also complete.')).toBeVisible()
})