import { useState } from 'react'
import { Trade } from '../services/api'

interface Props {
  trades: Trade[]
}

export default function TradeHistory({ trades }: Props) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'open' | 'closed'>('all')
  const [selected, setSelected] = useState<Trade | null>(null)

  const filtered = trades.filter((t) => {
    const matchSearch = t.pair.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || t.status === statusFilter
    return matchSearch && matchStatus
  })

  const exportCSV = () => {
    const headers = ['ID', 'Pair', 'Signal', 'Direction', 'Entry', 'SL', 'TP', 'PnL', 'Status', 'Opened', 'Probability']
    const rows = filtered.map((t) => [
      t.id, t.pair, t.signal, t.direction, t.entry_price, t.stop_loss,
      t.take_profit, t.pnl, t.status, t.opened_at, t.probability_score,
    ])
    const csv = [headers, ...rows].map((r) => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `trade-history-${Date.now()}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const pnlNum = (pnl: string | number) => Number(pnl) || 0

  return (
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
          {(['all', 'open', 'closed'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded text-xs font-mono font-semibold transition-all capitalize ${
                statusFilter === s
                  ? 'bg-zinc-700 text-white border border-zinc-600'
                  : 'text-zinc-500 border border-zinc-800 hover:border-zinc-700'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <button onClick={exportCSV} className="btn-primary flex items-center gap-2">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Export CSV
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-zinc-800/60">
              {['#', 'Pair', 'Signal', 'Entry', 'SL', 'TP', 'P&L', 'Status', 'Prob', 'Opened'].map((h) => (
                <th key={h} className="table-header text-left">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={10} className="text-center text-zinc-600 font-mono text-sm py-12">
                  No trades found
                </td>
              </tr>
            ) : (
              filtered.map((t) => {
                const pnl = pnlNum(t.pnl)
                const isBuy = (t.signal || t.direction || '').toUpperCase().includes('BUY') ||
                  t.direction === 'long'
                return (
                  <tr
                    key={t.id}
                    onClick={() => setSelected(t)}
                    className="border-b border-zinc-800/30 hover:bg-zinc-800/20 transition-colors cursor-pointer"
                  >
                    <td className="table-cell text-zinc-600">{t.id}</td>
                    <td className="table-cell font-semibold text-white">{t.pair?.toUpperCase()}</td>
                    <td className="table-cell">
                      <span className={isBuy ? 'signal-buy' : 'signal-sell'}>
                        {(t.signal || t.direction || '—').toUpperCase()}
                      </span>
                    </td>
                    <td className="table-cell">{Number(t.entry_price).toFixed(5)}</td>
                    <td className="table-cell text-red-400">{Number(t.stop_loss).toFixed(5)}</td>
                    <td className="table-cell text-emerald-400">{Number(t.take_profit).toFixed(5)}</td>
                    <td className={`table-cell font-bold ${pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                      {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}
                    </td>
                    <td className="table-cell">
                      <span className={`text-xs font-mono px-2 py-0.5 rounded border ${
                        t.status === 'open'
                          ? 'text-blue-400 bg-blue-400/10 border-blue-400/30'
                          : 'text-zinc-400 bg-zinc-800 border-zinc-700'
                      }`}>
                        {t.status?.toUpperCase()}
                      </span>
                    </td>
                    <td className="table-cell">
                      <span className={`text-xs font-mono font-bold ${
                        (t.probability_score ?? 0) >= 80 ? 'text-emerald-400' : 'text-yellow-400'
                      }`}>
                        {t.probability_score ?? '—'}%
                      </span>
                    </td>
                    <td className="table-cell text-zinc-500 text-xs">
                      {t.opened_at ? new Date(t.opened_at).toLocaleString() : '—'}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Trade Detail Modal */}
      {selected && (
        <div
          className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          onClick={() => setSelected(null)}
        >
          <div
            className="glass-card p-6 max-w-md w-full space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-white text-lg">
                {selected.pair?.toUpperCase()} — Trade #{selected.id}
              </h3>
              <button onClick={() => setSelected(null)} className="text-zinc-500 hover:text-white">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3 font-mono text-sm">
              {[
                ['Direction', selected.direction || selected.signal],
                ['Entry Price', Number(selected.entry_price).toFixed(5)],
                ['Stop Loss', Number(selected.stop_loss).toFixed(5)],
                ['Take Profit', Number(selected.take_profit).toFixed(5)],
                ['P&L', `${pnlNum(selected.pnl) >= 0 ? '+' : ''}${Number(selected.pnl).toFixed(2)}`],
                ['Status', selected.status?.toUpperCase()],
                ['Probability', `${selected.probability_score ?? '—'}%`],
                ['Opened', selected.opened_at ? new Date(selected.opened_at).toLocaleString() : '—'],
              ].map(([k, v]) => (
                <div key={k}>
                  <p className="text-zinc-600 text-xs uppercase">{k}</p>
                  <p className="text-zinc-200">{v}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="px-5 py-3 border-t border-zinc-800/60">
        <p className="text-xs text-zinc-600 font-mono">{filtered.length} trade(s)</p>
      </div>
    </div>
  )
}
