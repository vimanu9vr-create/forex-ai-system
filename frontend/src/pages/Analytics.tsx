import { useEffect, useState, useCallback } from 'react'
import { fetchAnalytics, AnalyticsData } from '../services/api'
import AnalyticsCharts from '../components/AnalyticsCharts'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const res = await fetchAnalytics()
      setData(res)
      setError('')
    } catch (e: any) {
      setError(e?.message || 'Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [load])

  if (loading) return <LoadingSpinner size="lg" text="Loading analytics..." />
  if (error && !data) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="text-zinc-500 text-sm font-mono mt-0.5">Performance metrics & statistics</p>
        </div>
        <button onClick={load} className="btn-primary flex items-center gap-2">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {error && <ErrorMessage message={error} />}
      {data && <AnalyticsCharts data={data} />}
    </div>
  )
}
