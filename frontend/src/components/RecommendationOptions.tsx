import type { RecommendationOption } from '../types/api'

type RecommendationOptionsProps = {
  recommendations: RecommendationOption[]
}

export function RecommendationOptions({ recommendations }: RecommendationOptionsProps) {
  return (
    <ol className="recommendation-options" aria-label="Possible books">
      {recommendations.map((recommendation) => (
        <li key={recommendation.title} className="recommendation-option">
          <h3>{recommendation.title}</h3>
          <p className="author">{recommendation.author}</p>
          <p>{recommendation.summary}</p>
        </li>
      ))}
    </ol>
  )
}