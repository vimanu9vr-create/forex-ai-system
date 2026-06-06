interface Props {
  message?: string
  onRetry?: () => void
}

export default function ErrorMessage({ message = 'Failed to load data', onRetry }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 p-8">
      <div className="flex items-center gap-2 text-red-400">
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-sm font-mono">{message}</span>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="btn-primary text-xs">
          Retry
        </button>
      )}
    </div>
  )
}
