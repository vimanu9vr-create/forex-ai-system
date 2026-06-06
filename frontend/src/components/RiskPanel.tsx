interface Props {
  openTrades: number
  winRate: number
  totalPnl: number
  avgProbability?: number
}

export default function RiskPanel({ openTrades, winRate, totalPnl, avgProbability }: Props) {
  const riskLevel =
    openTrades > 5 || winRate < 50 ? 'HIGH' : openTrades > 3 || winRate < 65 ? 'MEDIUM' : 'LOW'

  const riskColors = {
    LOW: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30',
    MEDIUM: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30',
    HIGH: 'text-red-400 bg-red-400/10 border-red-400/30',
  }

  const pnlPos = Number(totalPnl) >= 0

  return (
    <div className="glass-card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-white">Risk Monitor</p>
        <span className={`text-xs font-mono font-bold px-2 py-1 rounded border ${riskColors[riskLevel]}`}>
          {riskLevel} RISK
        </span>
      </div>

      <div className="space-y-3">
        {[
          {
            label: 'Open Exposure',
            value: `${openTrades} trades`,
            color: openTrades > 5 ? 'text-red-400' : 'text-zinc-300',
          },
          {
            label: 'Win Rate',
            value: `${winRate}%`,
            color: winRate >= 60 ? 'text-emerald-400' : 'text-yellow-400',
          },
          {
            label: 'Total P&L',
            value: `${pnlPos ? '+' : ''}$${Number(totalPnl).toLocaleString()}`,
            color: pnlPos ? 'text-emerald-400' : 'text-red-400',
          },
          ...(avgProbability !== undefined
            ? [{ label: 'Avg Probability', value: `${avgProbability}%`, color: 'text-blue-400' }]
            : []),
        ].map((row) => (
          <div key={row.label} className="flex justify-between items-center py-2 border-b border-zinc-800/40 last:border-0">
            <span className="text-xs text-zinc-500 font-mono">{row.label}</span>
            <span className={`text-sm font-mono font-semibold ${row.color}`}>{row.value}</span>
          </div>
        ))}
      </div>

      {/* Win rate bar */}
      <div>
        <div className="flex justify-between text-xs font-mono mb-1">
          <span className="text-zinc-600">Win Rate</span>
          <span className="text-zinc-400">{winRate}%</span>
        </div>
        <div className="bg-zinc-800 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${
              winRate >= 60 ? 'bg-emerald-400' : winRate >= 50 ? 'bg-yellow-400' : 'bg-red-400'
            }`}
            style={{ width: `${Math.min(winRate, 100)}%` }}
          />
        </div>
      </div>
    </div>
  )
}
