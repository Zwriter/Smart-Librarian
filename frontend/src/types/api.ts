export type ConversationRole = 'user' | 'assistant'

export type ConversationMessage = {
  role: ConversationRole
  content: string
}

export type ChatRequest = {
  question: string
  history: ConversationMessage[]
}

export type Recommendation = {
  title: string
  author: string
  rationale: string
  published_date?: string | null
  publisher?: string | null
}

export type RecommendationOption = {
  title: string
  author: string
  summary: string
}

export type ChatResponse = {
  recommendation: Recommendation | null
  recommendations?: RecommendationOption[] | null
  summary: string | null
  message?: string | null
}
