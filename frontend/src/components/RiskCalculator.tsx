import { useEffect, useMemo, useState } from 'react'
import { Signal } from '../services/api'

const PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'NZDUSD', 'USDCHF', 'XAUUSD']

/** Pip size for a pair (JPY pairs = 0.01, gold = 0.1, else 0.0001). */
function pipSizeFor(pair: string): number {
  const p = pair.toUpperCase()
  if (p.includes('XAU')) return 0.1
  return p.includes('JPY') ? 0.01 : 0.0001
}

/** Pip value per standard lot (100,000 units), in USD. */
function pipValuePerLot(pair: string, price: number): number {
  const p = pair.toUpperCase()
  const pip = pipSizeFor(p)
  const LOT = 100_000
  if (p.includes('XAU')) return 1 // gold ≈ $1/pip per 100oz lot (approx)
  if (p.endsWith('USD')) return pip * LOT // quote = USD → $10/pip (non-JPY)
  if (p.startsWith('USD') && price > 0) return (pip * LOT) / price // base = USD
  return pip * LOT // cross pair: approximate
}

interface Props {
  signals: Signal[]
}

const inputCls =
  'w-full bg-zinc-800/60 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white font-mono ' +
  'focus:border-emerald-500/50 focus:outline-none transition-colors'
const labelCls = 'text-xs text-zinc-500 font-mono uppercase tracking-wider mb-1.5 block'

export default function RiskCalculator({ signals }: Props) {
  const [balance, setBalance] = useState('1000')
  const [riskPct, setRiskPct] = useState('1')
  const [pair, setPair] = useState('EURUSD')
  const [entry, setEntry] = useState('')
  const [stopLoss, setStopLoss] = useState('')
  const [slPips, setSlPips] = useState('20')

  // When both entry & stop-loss prices are set, derive the stop distance in pips.
  useEffect(() => {
    const e = parseFloat(entry)
    const s = parseFloat(stopLoss)
    if (e > 0 && s > 0) setSlPips((Math.abs(e - s) / pipSizeFor(pair)).toFixed(1))
  }, [entry, stopLoss, pair])

  const loadSignal = (idx: number) => {
    const s = signals[idx]
    if (!s) return
    if (s.pair) setPair(s.pair.toUpperCase())
    if (s.entry != null) setEntry(String(s.entry))
    if (s.stop_loss != null) setStopLoss(String(s.stop_loss))
  }

  const r = useMemo(() => {
    const bal = parseFloat(balance) || 0
    const risk = parseFloat(riskPct) || 0
    const pips = parseFloat(slPips) || 0
    const e = parseFloat(entry)
    const s = parseFloat(stopLoss)

    const riskAmount = bal * (risk / 100)
    const pvLot = pipValuePerLot(pair, e > 0 ? e : 0)
    const lots = pips > 0 && pvLot > 0 ? riskAmount / (pips * pvLot) : 0
    const units = lots * 100_000
    const perPip = lots * pvLot
    const direction = e > 0 && s > 0 ? (s < e ? 'BUY' : 'SELL') : null

    return { riskAmount, pips, pvLot, lots, units, perPip, direction }
  }, [balance, riskPct, pair, entry, stopLoss, slPips])

  return (
    <div className="glass-card p-5">
      <div className="flex items-center gap-2 mb-4">
        <div className="p-1.5 rounded-lg border text-emerald-400 bg-emerald-400/10 border-emerald-400/20">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">Risk / Position Calculator</h3>
          <p className="text-xs text-zinc-500 font-mono">Lot size for a fixed % risk per trade</p>
        </div>
      </div>

      {/* Optional: load a live signal's levels */}
      {signals.length > 0 && (
        <div className="mb-4">
          <label className={labelCls}>Autofill from a live signal</label>
          <select
            className={inputCls}
            defaultValue=""
            onChange={(e) => e.target.value !== '' && loadSignal(Number(e.target.value))}
          >
            <option value="">— pick a signal —</option>
            {signals.map((s, i) => (
              <option key={i} value={i}>
                {s.pair?.toUpperCase()} {s.signal?.toUpperCase()} @ {s.entry} (SL {s.stop_loss})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Inputs */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <div>
          <label className={labelCls}>Account ($)</label>
          <input type="number" className={inputCls} value={balance}
            onChange={(e) => setBalance(e.target.value)} min="0" step="100" />
        </div>
        <div>
          <label className={labelCls}>Risk (%)</label>
          <input type="number" className={inputCls} value={riskPct}
            onChange={(e) => setRiskPct(e.target.value)} min="0" step="0.25" />
        </div>
        <div>
          <label className={labelCls}>Pair</label>
          <select className={inputCls} value={pair} onChange={(e) => setPair(e.target.value)}>
            {PAIRS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div>
          <label className={labelCls}>Entry</label>
          <input type="number" className={inputCls} value={entry} placeholder="optional"
            onChange={(e) => setEntry(e.target.value)} step="0.00001" />
        </div>
        <div>
          <label className={labelCls}>Stop Loss</label>
          <input type="number" className={inputCls} value={stopLoss} placeholder="optional"
            onChange={(e) => setStopLoss(e.target.value)} step="0.00001" />
        </div>
        <div>
          <label className={labelCls}>SL (pips)</label>
          <input type="number" className={inputCls} value={slPips}
            onChange={(e) => setSlPips(e.target.value)} min="0" step="1" />
        </div>
      </div>

      {/* Results */}
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
        <Result label="Risk amount" value={`$${r.riskAmount.toFixed(2)}`} accent="yellow" />
        <Result label="Stop (pips)" value={r.pips ? r.pips.toFixed(1) : '—'} accent="zinc" />
        <Result
          label="Position size"
          value={r.lots > 0 ? `${r.lots.toFixed(2)} lots` : '—'}
          sub={r.lots > 0 ? `${Math.round(r.units).toLocaleString()} units` : undefined}
          accent="emerald"
        />
        <Result
          label="Value / pip"
          value={r.perPip > 0 ? `$${r.perPip.toFixed(2)}` : '—'}
          sub={r.direction ? `${r.direction} side` : undefined}
          accent={r.direction === 'SELL' ? 'red' : 'blue'}
        />
      </div>

      <p className="text-[11px] text-zinc-600 font-mono mt-3 leading-relaxed">
        Risk ${r.riskAmount.toFixed(2)} ({riskPct || 0}% of ${balance || 0}) over a {r.pips || 0}-pip stop
        {r.lots > 0 ? <> → trade <span className="text-emerald-400">{r.lots.toFixed(2)} lots</span> ({Math.round(r.units).toLocaleString()} units).</> : '.'}
        {' '}Majors are exact; metals/crosses are approximate.
      </p>
    </div>
  )
}

function Result({
  label, value, sub, accent,
}: { label: string; value: string; sub?: string; accent: string }) {
  const colorMap: Record<string, string> = {
    emerald: 'text-emerald-400',
    red: 'text-red-400',
    blue: 'text-blue-400',
    yellow: 'text-yellow-400',
    zinc: 'text-zinc-200',
  }
  return (
    <div className="bg-zinc-800/40 border border-zinc-800 rounded-lg p-3">
      <p className="text-xs text-zinc-500 font-mono uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-xl font-bold font-mono ${colorMap[accent] || 'text-white'}`}>{value}</p>
      {sub && <p className="text-xs text-zinc-600 font-mono mt-0.5">{sub}</p>}
    </div>
  )
}
