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
      <p className="rationale">{recommendation.rationale}</p>
    </section>
  )
}