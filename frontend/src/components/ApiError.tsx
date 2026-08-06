type ApiErrorProps = {
  message: string
  isLoading: boolean
  onRetry: () => void
}

export function ApiError({ message, isLoading, onRetry }: ApiErrorProps) {
  return (
    <div className="api-error" id="api-error" role="alert" aria-live="assertive">
      <p>{message}</p>
      <button className="text-button" type="button" onClick={onRetry} disabled={isLoading}>
        Retry request
      </button>
    </div>
  )
}