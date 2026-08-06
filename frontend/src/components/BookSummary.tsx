type BookSummaryProps = {
  summary: string
}

export function BookSummary({ summary }: BookSummaryProps) {
  const paragraphs = summary.split(/\n{2,}/)

  return (
    <section className="summary" aria-labelledby="summary-title">
      <p className="result-label" id="summary-title">The long view</p>
      {paragraphs.map((paragraph, index) => (
        <p key={index}>{paragraph}</p>
      ))}
    </section>
  )
}