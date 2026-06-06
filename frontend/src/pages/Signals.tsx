import { useEffect, useState, useCallback } from 'react'
import { fetchSignals, Signal } from '../services/api'
import { useWebSocket } from '../hooks/useWebSocket'
import SignalsTable from '../components/SignalsTable'
import RiskCalculator from '../components/RiskCalculator'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

export default function Signals() {
  const [signals, setSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await fetchSignals()
      setSignals(Array.isArray(data) ? data : [])
      setLastUpdate(new Date())
      setError('')
    } catch (e: any) {
      setError(e?.message || 'Failed to load signals')
    } finally {
      setLoading(false)
    }
  }, [])

  // HTTP polling every 60 seconds (backend signals are cached for 5 min)
  useEffect(() => {
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [load])

  // WebSocket live updates
  useWebSocket({
    path: '/ws/signals',
    onMessage: (data: any) => {
      if (data?.signals && Array.isArray(data.signals)) {
        setSignals(data.signals)
        setLastUpdate(new Date())
      }
    },
  })

  const buyCount = signals.filter((s) => s.signal?.toUpperCase() === 'BUY').length
  const sellCount = signals.filter((s) => s.signal?.toUpperCase() === 'SELL').length
  const highProb = signals.filter((s) => (s.confluence_score ?? 0) >= 85).length

  if (loading) return <LoadingSpinner size="lg" text="Loading signals..." />

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Live Signals</h1>
          <p className="text-zinc-500 text-sm font-mono mt-0.5">
            {lastUpdate ? `Updated ${lastUpdate.toLocaleTimeString()}` : 'Loading...'}
          </p>
        </div>
        <button onClick={load} className="btn-primary flex items-center gap-2">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Signals', value: signals.length, color: 'text-white' },
          { label: 'BUY Signals', value: buyCount, color: 'text-emerald-400' },
          { label: 'SELL Signals', value: sellCount, color: 'text-red-400' },
          { label: 'High Conf (≥85)', value: highProb, color: 'text-yellow-400' },
        ].map((s) => (
          <div key={s.label} className="stat-card">
            <p className="text-xs text-zinc-500 font-mono uppercase tracking-wider mb-1">{s.label}</p>
            <p className={`text-3xl font-bold font-mono ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {error && <ErrorMessage message={error} onRetry={load} />}

      <RiskCalculator signals={signals} />

      <SignalsTable signals={signals} onExecute={load} />
    </div>
  )
}
