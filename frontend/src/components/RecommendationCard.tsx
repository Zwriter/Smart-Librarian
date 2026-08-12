import type { Recommendation } from '../types/api'

type RecommendationCardProps = {
  recommendation: Recommendation
}

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  return (
    <section className="recommendation" aria-labelledby="recommendation-title">
      <p className="result-label">Recommended title</p>
      <h3 id="recommendation-title">{recommendation.title}</h3>
      <p className="author">{recommendation.author}</p>
      {(recommendation.published_date || recommendation.publisher) && (
        <p className="book-details">
          {recommendation.published_date && (
            <span>Published {recommendation.published_date}</span>
          )}
          {recommendation.published_date && recommendation.publisher && <span aria-hidden="true"> · </span>}
          {recommendation.publisher && <span>{recommendation.publisher}</span>}
        </p>
      )}
      <p className="rationale">{recommendation.rationale}</p>
    </section>
  )
}