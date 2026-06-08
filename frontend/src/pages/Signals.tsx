import { useEffect, useState, useCallback } from 'react'
import { fetchSignals, fetchIntradaySignals, Signal } from '../services/api'
import { useWebSocket } from '../hooks/useWebSocket'
import SignalsTable from '../components/SignalsTable'
import RiskCalculator from '../components/RiskCalculator'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

type Mode = 'daily' | 'intraday'

export default function Signals() {
  const [mode, setMode] = useState<Mode>('daily')
  const [entryTf, setEntryTf] = useState<'15min' | '5min'>('15min')
  const [session, setSession] = useState<'london' | 'newyork' | 'both'>('london')
  const [signals, setSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  const load = useCallback(async () => {
    try {
      const data = mode === 'intraday' ? await fetchIntradaySignals(entryTf, session) : await fetchSignals()
      setSignals(Array.isArray(data) ? data : [])
      setLastUpdate(new Date())
      setError('')
    } catch (e: any) {
      setError(e?.message || 'Failed to load signals')
    } finally {
      setLoading(false)
    }
  }, [mode, entryTf, session])

  // Reload whenever the engine mode changes
  useEffect(() => {
    setLoading(true)
    setSignals([])
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [load])

  // WebSocket live updates — only the daily engine pushes; ignore while on intraday
  useWebSocket({
    path: '/ws/signals',
    onMessage: (data: any) => {
      if (mode !== 'daily') return
      if (data?.signals && Array.isArray(data.signals)) {
        setSignals(data.signals)
        setLastUpdate(new Date())
      }
    },
  })

  const buyCount = signals.filter((s) => s.signal?.toUpperCase() === 'BUY').length
  const sellCount = signals.filter((s) => s.signal?.toUpperCase() === 'SELL').length
  const highProb = signals.filter((s) => (s.confluence_score ?? 0) >= 85).length

  const isIntraday = mode === 'intraday'
  const sessionLabel = session === 'newyork' ? 'New York' : session === 'both' ? 'London + New York' : 'London'

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
        <div className="flex items-center gap-3">
          {/* Engine toggle */}
          <div className="flex gap-1 p-1 rounded-lg bg-zinc-900 border border-zinc-800">
            {([
              ['daily', 'Daily Edge'],
              ['intraday', 'Liquidity Sweeps'],
            ] as [Mode, string][]).map(([m, label]) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-3 py-1.5 rounded text-xs font-mono font-semibold transition-all ${
                  mode === m
                    ? 'bg-zinc-700 text-white border border-zinc-600'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <button onClick={load} className="btn-primary flex items-center gap-2">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Engine context banner */}
      {isIntraday ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3 space-y-2">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <p className="text-sm text-amber-300 font-semibold">⚡ Top-Down Liquidity Sweeps — experimental</p>
            <div className="flex items-center gap-2 flex-wrap">
              {/* Session toggle — analyze London & New York separately */}
              <div className="flex gap-1 p-1 rounded bg-zinc-900 border border-zinc-800">
                {([
                  ['london', 'London'],
                  ['newyork', 'New York'],
                  ['both', 'Both'],
                ] as ['london' | 'newyork' | 'both', string][]).map(([s, label]) => (
                  <button
                    key={s}
                    onClick={() => setSession(s)}
                    className={`px-2.5 py-1 rounded text-xs font-mono font-semibold transition-all ${
                      session === s ? 'bg-zinc-700 text-white border border-zinc-600' : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {/* Entry timeframe toggle */}
              <div className="flex gap-1 p-1 rounded bg-zinc-900 border border-zinc-800">
                {(['15min', '5min'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setEntryTf(t)}
                    className={`px-2.5 py-1 rounded text-xs font-mono font-semibold transition-all ${
                      entryTf === t ? 'bg-zinc-700 text-white border border-zinc-600' : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    {t === '15min' ? '15m' : '5m'}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <p className="text-xs text-zinc-400 font-mono leading-relaxed">
            Daily/4H bias gates direction — mixed HTF means the pair stands aside. Sweep → displacement → MSS →
            FVG/OTE entry in the <span className="text-amber-300">{sessionLabel} killzone</span>; wider sweep-stop,
            TP at the nearest opposing liquidity, runner to the HTF draw. Entry TF:{' '}
            <span className="text-amber-300">{entryTf === '15min' ? '15-minute' : '5-minute'}</span> · paper / forward-test.
          </p>
          {session === 'london' ? (
            <p className="text-xs text-emerald-300/80 font-mono">
              ✓ London is the validated session — positive net-of-cost &amp; out-of-sample on a small sample (19 trades), not real-money cleared.
            </p>
          ) : (
            <p className="text-xs text-red-300/90 font-mono">
              ⚠ {session === 'both' ? 'The New York portion is' : 'New York is'} analysis-only — a net loser in the backtest. London is the validated session.
            </p>
          )}
        </div>
      ) : (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
          <p className="text-xs text-zinc-400 font-mono leading-relaxed">
            Daily Edge — the cost &amp; out-of-sample validated engine (GBPUSD / EURUSD daily). Structure-based entries
            with ≥1:3 R:R.
          </p>
        </div>
      )}

      {/* Quick stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Signals', value: signals.length, color: 'text-white' },
          { label: 'BUY Signals', value: buyCount, color: 'text-emerald-400' },
          { label: 'SELL Signals', value: sellCount, color: 'text-red-400' },
          { label: isIntraday ? 'High Quality (≥85)' : 'High Conf (≥85)', value: highProb, color: 'text-yellow-400' },
        ].map((s) => (
          <div key={s.label} className="stat-card">
            <p className="text-xs text-zinc-500 font-mono uppercase tracking-wider mb-1">{s.label}</p>
            <p className={`text-3xl font-bold font-mono ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {error && <ErrorMessage message={error} onRetry={load} />}

      {loading ? (
        <LoadingSpinner size="lg" text="Loading signals..." />
      ) : (
        <>
          <RiskCalculator signals={signals} />
          <SignalsTable signals={signals} onExecute={load} />
        </>
      )}
    </div>
  )
}
