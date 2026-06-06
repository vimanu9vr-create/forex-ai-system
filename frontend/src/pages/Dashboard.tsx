import { useEffect, useState, useCallback } from 'react'
import { fetchDashboard, fetchTelegramLogs, DashboardData } from '../services/api'
import DashboardCards from '../components/DashboardCards'
import TradingChart from '../components/TradingChart'
import TelegramLogs from '../components/TelegramLogs'
import RiskPanel from '../components/RiskPanel'
import SchedulerPanel from '../components/SchedulerPanel'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const [dash, telegramData] = await Promise.all([
        fetchDashboard(),
        fetchTelegramLogs(20),
      ])
      setData(dash)
      setLogs(telegramData.logs || [])
      setError('')
    } catch (e: any) {
      setError(e?.message || 'Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [load])

  if (loading) return <LoadingSpinner size="lg" text="Loading dashboard..." />
  if (error && !data) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Trading Dashboard</h1>
          <p className="text-zinc-500 text-sm font-mono mt-0.5">Real-time system overview</p>
        </div>
        <button
          onClick={load}
          className="btn-primary flex items-center gap-2"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* KPI Cards */}
      {data && <DashboardCards data={data} />}

      {/* Live chart — full width, large */}
      <TradingChart />

      {/* Supporting panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {data && (
          <RiskPanel
            openTrades={data.open_trades ?? 0}
            winRate={data.win_rate ?? 0}
            totalPnl={data.total_pnl ?? 0}
          />
        )}
        <SchedulerPanel />
        <TelegramLogs logs={logs} />
      </div>
    </div>
  )
}
