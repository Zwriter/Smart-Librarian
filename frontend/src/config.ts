function readPositiveInteger(value: string | undefined, fallback: number): number {
  const parsedValue = Number(value)
  return Number.isInteger(parsedValue) && parsedValue > 0 ? parsedValue : fallback
}

export const frontendConfig = {
  maxHistoryMessages: readPositiveInteger(import.meta.env.VITE_MAX_HISTORY_MESSAGES, 20),
  maxQuestionLength: readPositiveInteger(import.meta.env.VITE_MAX_QUESTION_LENGTH, 500),
} as const