export type RequestStatus = 'idle' | 'loading' | 'success' | 'error'

export type LoadingState = {
  isLoading: boolean
}

export type ErrorState = {
  error: string | null
}
