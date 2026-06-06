import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line,
} from 'recharts'
import { AnalyticsData } from '../services/api'

interface Props {
  data: AnalyticsData
}

const COLORS = ['#00ff88', '#00d4ff', '#8b5cf6', '#ffd600', '#ff4466']

export default function AnalyticsCharts({ data }: Props) {
  const directionData = [
    { name: 'BUY', value: data.buy_trades },
    { name: 'SELL', value: data.sell_trades },
  ]

  const statusData = [
    { name: 'Open', value: data.open_trades },
    { name: 'Closed', value: data.closed_trades },
  ]

  const pairData = (data.pair_stats || [])
    .sort((a, b) => b.trades - a.trades)
    .slice(0, 10)

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload?.length) {
      return (
        <div className="glass-card px-3 py-2 text-xs font-mono">
          <p className="text-zinc-400">{label}</p>
          {payload.map((p: any) => (
            <p key={p.dataKey} style={{ color: p.color }}>
              {p.name}: {p.value}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-6">
      {/* Summary stats row */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {[
          { label: 'Total Trades', value: data.total_trades, color: 'text-white' },
          { label: 'Avg Probability', value: `${data.avg_probability}%`, color: 'text-emerald-400' },
          { label: 'Open / Closed', value: `${data.open_trades} / ${data.closed_trades}`, color: 'text-blue-400' },
        ].map((s) => (
          <div key={s.label} className="stat-card">
            <p className="text-xs text-zinc-500 font-mono uppercase tracking-wider mb-1">{s.label}</p>
            <p className={`text-2xl font-bold font-mono ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pair Performance */}
        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Trades by Pair</h3>
          {pairData.length === 0 ? (
            <p className="text-zinc-600 font-mono text-sm text-center py-8">No pair data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={pairData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="pair" tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'monospace' }} />
                <YAxis tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'monospace' }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="trades" fill="#00ff88" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Direction split */}
        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Buy vs Sell</h3>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={directionData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={4}
                dataKey="value"
              >
                {directionData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                formatter={(value) => (
                  <span className="text-xs font-mono text-zinc-400">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Open vs Closed */}
        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Open vs Closed Trades</h3>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={statusData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={4}
                dataKey="value"
              >
                <Cell fill="#00d4ff" />
                <Cell fill="#71717a" />
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                formatter={(value) => (
                  <span className="text-xs font-mono text-zinc-400">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Probability distribution (top pairs) */}
        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Top 5 Pairs by Volume</h3>
          {pairData.length === 0 ? (
            <p className="text-zinc-600 font-mono text-sm text-center py-8">No data yet</p>
          ) : (
            <div className="space-y-3 mt-2">
              {pairData.slice(0, 5).map((p, i) => {
                const max = pairData[0]?.trades || 1
                const pct = Math.round((p.trades / max) * 100)
                return (
                  <div key={p.pair} className="space-y-1">
                    <div className="flex justify-between text-xs font-mono">
                      <span className="text-zinc-400">{p.pair?.toUpperCase()}</span>
                      <span style={{ color: COLORS[i % COLORS.length] }}>{p.trades} trades</span>
                    </div>
                    <div className="bg-zinc-800 rounded-full h-1.5">
                      <div
                        className="h-1.5 rounded-full transition-all"
                        style={{ width: `${pct}%`, background: COLORS[i % COLORS.length] }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
