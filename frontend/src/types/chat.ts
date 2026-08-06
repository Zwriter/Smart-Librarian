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
}

export type ChatResponse = {
  recommendation: Recommendation
  summary: string
}