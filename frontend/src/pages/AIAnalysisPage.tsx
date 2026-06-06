import { useEffect, useState, useCallback } from 'react'
import { fetchAIAnalysis, AIAnalysisData } from '../services/api'
import AIAnalysis from '../components/AIAnalysis'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

export default function AIAnalysisPage() {
  const [data, setData] = useState<AIAnalysisData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchAIAnalysis()
      setData(res)
      setError('')
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to fetch AI analysis')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [load])

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">AI Analysis</h1>
          <p className="text-zinc-500 text-sm font-mono mt-0.5">
            BOS · CHOCH · Liquidity · Session Intelligence
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="btn-primary flex items-center gap-2 disabled:opacity-50"
        >
          {loading ? (
            <div className="w-3.5 h-3.5 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
          ) : (
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          )}
          {loading ? 'Analyzing...' : 'Re-analyze'}
        </button>
      </div>

      {loading && !data && <LoadingSpinner size="lg" text="Running AI analysis..." />}
      {error && !data && <ErrorMessage message={error} onRetry={load} />}
      {error && data && (
        <div className="flex items-center gap-2 text-yellow-400 text-xs font-mono bg-yellow-400/5 border border-yellow-400/20 rounded-lg px-3 py-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          Refresh failed — showing cached data
        </div>
      )}
      {data && <AIAnalysis data={data} />}
    </div>
  )
}
