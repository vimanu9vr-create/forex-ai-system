import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Signal, executeSignalTrade, validateIntradaySignal, IntradayVerdict, redetectIntradaySignal, RedetectResult } from '../services/api'

interface Props {
  signals: Signal[]
  onExecute?: () => void
}

function gradeColor(g?: string): string {
  if (g === 'A+') return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
  if (g === 'A') return 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
  return 'bg-zinc-700/40 text-zinc-300 border border-zinc-600/40'
}

function biasLabel(bias: Signal['bias']): string {
  if (!bias) return '—'
  if (typeof bias === 'string') return bias
  if (typeof bias === 'object') {
    const b = (bias as Record<string, unknown>)
    return String(b.bias || b.direction || JSON.stringify(bias)).toUpperCase()
  }
  return '—'
}

// Watch rows (no A+ entry) carry 0 levels — render those as an em dash, not 0.00000.
const fmt = (n: number | undefined | null) => (n && Number(n) !== 0 ? Number(n).toFixed(5) : '—')

export default function SignalsTable({ signals, onExecute }: Props) {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'ALL' | 'BUY' | 'SELL'>('ALL')
  const [sortBy, setSortBy] = useState<'probability' | 'pair'>('probability')
  const [executing, setExecuting] = useState<string | null>(null)
  const [selected, setSelected] = useState<Signal | null>(null)
  const [verdict, setVerdict] = useState<IntradayVerdict | null>(null)
  const [validating, setValidating] = useState(false)
  const [redetect, setRedetect] = useState<RedetectResult | null>(null)
  const [redetecting, setRedetecting] = useState(false)

  const openDetail = (signal: Signal) => {
    setSelected(signal)
    setVerdict(null)
    setRedetect(null)
  }

  const handleValidate = async () => {
    if (!selected) return
    setValidating(true)
    setVerdict(null)
    try {
      setVerdict(await validateIntradaySignal(selected))
    } catch {
      setVerdict({ verdict: 'ERROR', confidence: 0, reason: 'Validation request failed — is the backend running?' })
    } finally {
      setValidating(false)
    }
  }

  const handleRedetect = async () => {
    if (!selected) return
    setRedetecting(true)
    setRedetect(null)
    try {
      const tf = selected.timeframe || '15min'
      const kz = String(selected.killzone || '')
      const session = kz.includes('New York') ? 'newyork' : 'london'
      setRedetect(await redetectIntradaySignal(selected.pair, tf, session))
    } catch {
      setRedetect({ verdict: 'ERROR', reason: 'Re-detection request failed — is the backend running?' })
    } finally {
      setRedetecting(false)
    }
  }

  const filtered = signals
    .filter((s) => {
      const matchSearch = s.pair.toLowerCase().includes(search.toLowerCase())
      const matchFilter = filter === 'ALL' || s.signal.toUpperCase() === filter
      return matchSearch && matchFilter
    })
    .sort((a, b) =>
      sortBy === 'probability'
        ? b.confluence_score - a.confluence_score
        : a.pair.localeCompare(b.pair),
    )

  const handleExecute = async (signal: Signal, e: React.MouseEvent) => {
    e.stopPropagation()
    const key = `${signal.pair}-${signal.signal}`
    setExecuting(key)
    try {
      await executeSignalTrade({
        pair: signal.pair,
        signal: signal.signal,
        entry: signal.entry,
        stop_loss: signal.stop_loss,
        take_profit: signal.take_profit,
        probability: signal.confluence_score,
        units: 1000,
      })
      onExecute?.()
    } catch (err) {
      console.error('Execute trade failed', err)
    } finally {
      setExecuting(null)
    }
  }

  return (
    <>
      <div className="glass-card overflow-hidden">
        {/* Controls */}
        <div className="px-5 py-4 border-b border-zinc-800/60 flex flex-wrap items-center gap-3">
          <input
            type="text"
            placeholder="Search pair..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-field max-w-[180px]"
          />
          <div className="flex gap-1.5">
            {(['ALL', 'BUY', 'SELL'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 rounded text-xs font-mono font-semibold transition-all ${
                  filter === f
                    ? f === 'BUY'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                      : f === 'SELL'
                      ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                      : 'bg-zinc-700 text-white border border-zinc-600'
                    : 'text-zinc-500 border border-zinc-800 hover:border-zinc-700'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          <div className="flex-1" />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'probability' | 'pair')}
            className="input-field max-w-[160px]"
          >
            <option value="probability">Sort: Confluence</option>
            <option value="pair">Sort: Pair</option>
          </select>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-zinc-800/60">
                {['Pair', 'Signal', 'Entry', 'Stop Loss', 'Take Profit', 'Confluence', 'Session', 'R:R', 'TF', 'Action'].map((h) => (
                  <th key={h} className="table-header text-left whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <AnimatePresence>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="text-center text-zinc-600 font-mono text-sm py-12">
                      No signals — backend scanner may be warming up
                    </td>
                  </tr>
                ) : (
                  filtered.map((signal, i) => {
                    const isBuy = signal.signal.toUpperCase() === 'BUY'
                    const execKey = `${signal.pair}-${signal.signal}`
                    const isExecuting = executing === execKey
                    const prob = signal.confluence_score ?? 0
                    const probColor =
                      prob >= 85 ? 'text-emerald-400' : prob >= 70 ? 'text-yellow-400' : 'text-red-400'

                    return (
                      <motion.tr
                        key={`${signal.pair}-${i}`}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => openDetail(signal)}
                        className="border-b border-zinc-800/30 hover:bg-zinc-800/20 transition-colors cursor-pointer"
                      >
                        <td className="table-cell font-semibold text-white">
                          <div className="flex items-center gap-1.5">
                            <span>{signal.pair.toUpperCase()}</span>
                            {signal.grade && (
                              <span className={`text-[10px] font-bold font-mono px-1 py-0.5 rounded ${gradeColor(signal.grade)}`}>
                                {signal.grade}
                              </span>
                            )}
                            {signal.fresh === false && (
                              <span className="text-[10px] text-amber-500/80 font-mono" title={`stale (${signal.candle_age_min}m old)`}>
                                stale
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="table-cell">
                          <span className={isBuy ? 'signal-buy' : 'signal-sell'}>
                            {signal.signal.toUpperCase()}
                          </span>
                        </td>
                        <td className="table-cell">{fmt(signal.entry)}</td>
                        <td className="table-cell text-red-400">{fmt(signal.stop_loss)}</td>
                        <td className="table-cell text-emerald-400">{fmt(signal.take_profit)}</td>
                        <td className="table-cell">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-zinc-800 rounded-full h-1.5 max-w-[60px]">
                              <div
                                className={`h-1.5 rounded-full ${prob >= 85 ? 'bg-emerald-400' : prob >= 70 ? 'bg-yellow-400' : 'bg-red-400'}`}
                                style={{ width: `${prob}%` }}
                              />
                            </div>
                            <span className={`text-xs font-bold font-mono ${probColor}`}>{prob}%</span>
                          </div>
                        </td>
                        <td className="table-cell text-xs text-zinc-400">{signal.session || '—'}</td>
                        <td className="table-cell text-xs text-blue-400">{signal.risk_reward || '—'}</td>
                        <td className="table-cell">
                          <span className="text-xs font-mono text-zinc-500 border border-zinc-800 rounded px-1.5 py-0.5">
                            {signal.timeframe || '—'}
                          </span>
                        </td>
                        <td className="table-cell" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={(e) => handleExecute(signal, e)}
                            disabled={isExecuting || signal.entry === 0}
                            className={`text-xs px-3 py-1.5 rounded border font-mono font-semibold transition-all ${
                              isBuy
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
                                : 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/20'
                            } disabled:opacity-40 disabled:cursor-not-allowed`}
                            title={signal.entry === 0 ? 'No entry price available' : 'Execute trade on OANDA'}
                          >
                            {isExecuting ? '...' : 'EXECUTE'}
                          </button>
                        </td>
                      </motion.tr>
                    )
                  })
                )}
              </AnimatePresence>
            </tbody>
          </table>
        </div>

        <div className="px-5 py-3 border-t border-zinc-800/60 flex items-center justify-between">
          <p className="text-xs text-zinc-600 font-mono">{filtered.length} live signal(s) from Smart Money scanner</p>
          <p className="text-xs text-zinc-600 font-mono">Auto-refresh 10s · WS live</p>
        </div>
      </div>

      {/* Detail modal */}
      {selected && (
        <div
          className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          onClick={() => setSelected(null)}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card p-6 max-w-lg w-full space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h3 className="font-bold text-white text-lg">{selected.pair.toUpperCase()}</h3>
                <span className={selected.signal.toUpperCase() === 'BUY' ? 'signal-buy' : 'signal-sell'}>
                  {selected.signal.toUpperCase()}
                </span>
              </div>
              <button onClick={() => setSelected(null)} className="text-zinc-500 hover:text-white">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 font-mono text-sm">
              {([
                ['Entry Price', fmt(selected.entry), 'text-white'],
                ['Stop Loss', fmt(selected.stop_loss), 'text-red-400'],
                ['Take Profit', fmt(selected.take_profit), 'text-emerald-400'],
                ['Confluence', `${selected.confluence_score}%`, selected.confluence_score >= 85 ? 'text-emerald-400' : 'text-yellow-400'],
                ['Risk/Reward', String(selected.risk_reward || '—'), 'text-blue-400'],
                ['Session', selected.session || '—', 'text-zinc-300'],
                ['Timeframe', selected.timeframe || '—', 'text-zinc-300'],
                ['Model', selected.model || 'Smart Money AI', 'text-purple-400'],
                ['Bias', biasLabel(selected.bias), 'text-zinc-300'],
                ['Updated', selected.updated_at ? new Date(selected.updated_at).toLocaleTimeString() : '—', 'text-zinc-500'],
                ...(selected.entry_basis ? [['Entry Basis', selected.entry_basis, 'text-purple-300'] as [string, string, string]] : []),
                ...(selected.swept_liquidity ? [['Swept Liq', Number(selected.swept_liquidity).toFixed(5), 'text-zinc-300'] as [string, string, string]] : []),
                ...(selected.mss_level ? [['MSS Level', Number(selected.mss_level).toFixed(5), 'text-zinc-300'] as [string, string, string]] : []),
                ...(selected.htf_bias ? [['HTF Bias', String(selected.htf_bias).toUpperCase(), 'text-blue-300'] as [string, string, string]] : []),
                ...(selected.target_basis ? [['Target', selected.target_basis, 'text-emerald-300'] as [string, string, string]] : []),
                ...(selected.runner_target ? [['Runner Target', Number(selected.runner_target).toFixed(5), 'text-zinc-300'] as [string, string, string]] : []),
                ...(selected.grade ? [['Grade', selected.grade, 'text-yellow-300'] as [string, string, string]] : []),
                ...(selected.risk_pips ? [['Risk (pips)', String(selected.risk_pips), 'text-red-300'] as [string, string, string]] : []),
              ] as [string, string, string][]).map(([k, v, c]) => (
                <div key={k}>
                  <p className="text-zinc-600 text-xs uppercase mb-0.5">{k}</p>
                  <p className={c}>{v}</p>
                </div>
              ))}
            </div>

            {selected.setup && (
              <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2">
                <p className="text-zinc-600 text-xs uppercase mb-1">Setup</p>
                <p className="text-zinc-300 text-xs font-mono leading-relaxed">{selected.setup}</p>
              </div>
            )}

            {selected.management && (
              <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 px-3 py-2">
                <p className="text-zinc-600 text-xs uppercase mb-1">Trade Management</p>
                <p className="text-zinc-300 text-xs font-mono leading-relaxed">{selected.management}</p>
              </div>
            )}

            {/* Crew validation — intraday signals only (carry an entry_basis) */}
            {selected.entry_basis && (
              <div className="space-y-2">
                <button
                  onClick={handleValidate}
                  disabled={validating}
                  className="w-full py-2 rounded-lg font-mono font-semibold text-sm bg-purple-500/15 text-purple-300 border border-purple-500/30 hover:bg-purple-500/25 transition-all disabled:opacity-50"
                >
                  {validating ? 'Consulting desk crew…' : '🧠 AI Validate (Crew)'}
                </button>
                {verdict && (
                  <div className={`rounded-lg border px-3 py-2 ${
                    verdict.verdict === 'TAKE'
                      ? 'border-emerald-500/40 bg-emerald-500/5'
                      : verdict.verdict === 'SKIP'
                      ? 'border-red-500/40 bg-red-500/5'
                      : 'border-zinc-700 bg-zinc-900/50'
                  }`}>
                    <div className="flex items-center justify-between">
                      <span className={`font-bold font-mono ${
                        verdict.verdict === 'TAKE' ? 'text-emerald-400' : verdict.verdict === 'SKIP' ? 'text-red-400' : 'text-zinc-300'
                      }`}>{verdict.verdict}</span>
                      <span className="text-xs text-zinc-500 font-mono">{verdict.confidence}% · {verdict.source || 'crew'}</span>
                    </div>
                    <p className="text-xs text-zinc-300 mt-1 leading-relaxed">{verdict.reason}</p>
                  </div>
                )}

                <button
                  onClick={handleRedetect}
                  disabled={redetecting}
                  className="w-full py-2 rounded-lg font-mono font-semibold text-sm bg-sky-500/15 text-sky-300 border border-sky-500/30 hover:bg-sky-500/25 transition-all disabled:opacity-50"
                >
                  {redetecting ? 'Re-detecting independently…' : '🔎 2nd Opinion (independent re-detect)'}
                </button>
                {redetect && (
                  <div className={`rounded-lg border px-3 py-2 ${
                    redetect.verdict === 'CONFIRM'
                      ? 'border-emerald-500/40 bg-emerald-500/5'
                      : redetect.verdict === 'REJECT'
                      ? 'border-red-500/40 bg-red-500/5'
                      : 'border-zinc-700 bg-zinc-900/50'
                  }`}>
                    <div className="flex items-center justify-between">
                      <span className={`font-bold font-mono ${
                        redetect.verdict === 'CONFIRM' ? 'text-emerald-400' : redetect.verdict === 'REJECT' ? 'text-red-400' : 'text-zinc-300'
                      }`}>
                        {redetect.verdict}{redetect.direction && redetect.direction !== 'NONE' ? ` ${redetect.direction}` : ''}
                      </span>
                      <span className="text-xs text-zinc-500 font-mono">{redetect.confidence ?? 0}% · {redetect.source || 'crew'}</span>
                    </div>
                    {redetect.agreement && (
                      <p className={`text-xs font-mono mt-1 ${redetect.agreement.startsWith('AGREE') ? 'text-emerald-300' : 'text-amber-300'}`}>
                        {redetect.agreement.startsWith('AGREE') ? '✓ ' : '⚠ '}{redetect.agreement}
                      </p>
                    )}
                    {redetect.verdict === 'CONFIRM' && redetect.entry != null && (
                      <p className="text-xs text-zinc-400 font-mono mt-1">
                        its read — E {redetect.entry} · SL {redetect.stop_loss} · TP {redetect.take_profit}
                      </p>
                    )}
                    {redetect.reason && <p className="text-xs text-zinc-300 mt-1 leading-relaxed">{redetect.reason}</p>}
                  </div>
                )}
              </div>
            )}

            {selected.entry > 0 && (
              <button
                onClick={(e) => { handleExecute(selected, e); setSelected(null) }}
                className={`w-full py-2.5 rounded-lg font-mono font-semibold text-sm transition-all ${
                  selected.signal.toUpperCase() === 'BUY'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 hover:bg-emerald-500/30'
                    : 'bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30'
                }`}
              >
                Execute {selected.signal.toUpperCase()} on OANDA
              </button>
            )}
          </motion.div>
        </div>
      )}
    </>
  )
}
