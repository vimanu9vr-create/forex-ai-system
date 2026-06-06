import { useEffect, useState, useCallback } from 'react'
import { fetchTradeHistory, Trade } from '../services/api'
import TradeHistory from '../components/TradeHistory'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

export default function Trades() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [limit, setLimit] = useState(50)

  const load = useCallback(async () => {
    try {
      const data = await fetchTradeHistory(limit)
      setTrades(Array.isArray(data) ? data : [])
      setError('')
    } catch (e: any) {
      setError(e?.message || 'Failed to load trade history')
    } finally {
      setLoading(false)
    }
  }, [limit])

  useEffect(() => {
    load()
  }, [load])

  const totalPnl = trades.reduce((sum, t) => sum + (Number(t.pnl) || 0), 0)
  const openCount = trades.filter((t) => t.status === 'open').length

  if (loading) return <LoadingSpinner size="lg" text="Loading trades..." />

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Trade History</h1>
          <p className="text-zinc-500 text-sm font-mono mt-0.5">{trades.length} trades loaded</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="input-field max-w-[120px]"
          >
            {[25, 50, 100, 200].map((n) => (
              <option key={n} value={n}>Last {n}</option>
            ))}
          </select>
          <button onClick={load} className="btn-primary flex items-center gap-2">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {[
          { label: 'Total Trades', value: trades.length, color: 'text-white' },
          { label: 'Open Trades', value: openCount, color: 'text-blue-400' },
          {
            label: 'Total P&L',
            value: `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`,
            color: totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400',
          },
        ].map((s) => (
          <div key={s.label} className="stat-card">
            <p className="text-xs text-zinc-500 font-mono uppercase tracking-wider mb-1">{s.label}</p>
            <p className={`text-2xl font-bold font-mono ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {error && <ErrorMessage message={error} onRetry={load} />}
      <TradeHistory trades={trades} />
    </div>
  )
}
