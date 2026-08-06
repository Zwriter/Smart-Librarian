export function LoadingIndicator() {
  return (
    <div className="loading" role="status" aria-live="polite" aria-atomic="true">
      Searching the stacks<span aria-hidden="true">...</span>
    </div>
  )
}