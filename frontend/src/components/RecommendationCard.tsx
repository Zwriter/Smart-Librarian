import type { Recommendation } from '../types/api'

type RecommendationCardProps = {
  recommendation: Recommendation
}

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const language = recommendation.language
    ? new Intl.DisplayNames(['en'], { type: 'language' }).of(recommendation.language) ?? recommendation.language
    : null

  return (
    <section className="recommendation" aria-labelledby="recommendation-title">
      <p className="result-label">Recommended title</p>
      <h3 id="recommendation-title">{recommendation.title}</h3>
      <p className="author">{recommendation.author}</p>
      {(recommendation.published_date || recommendation.publisher || language) && (
        <p className="book-details">
          {recommendation.published_date && (
            <span>Published {recommendation.published_date}</span>
          )}
          {recommendation.published_date && recommendation.publisher && <span aria-hidden="true"> · </span>}
          {recommendation.publisher && <span>{recommendation.publisher}</span>}
          {language && (recommendation.published_date || recommendation.publisher) && <span aria-hidden="true"> · </span>}
          {language && <span>Language: {language}</span>}
        </p>
      )}
      <p className="rationale">{recommendation.rationale}</p>
    </section>
  )
}