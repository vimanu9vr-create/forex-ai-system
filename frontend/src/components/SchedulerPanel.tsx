import { useEffect, useState, useCallback } from 'react'
import api from '../services/api'

interface SchedulerStatus {
  running: boolean
  interval_seconds: number
  interval_minutes: number
}

export default function SchedulerPanel() {
  const [status, setStatus] = useState<SchedulerStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [alertLoading, setAlertLoading] = useState(false)
  const [alertResult, setAlertResult] = useState<string | null>(null)

  const loadStatus = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get<SchedulerStatus>('/scheduler/status')
      setStatus(res.data)
    } catch {
      // backend may not be running
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStatus()
    const t = setInterval(loadStatus, 15000)
    return () => clearInterval(t)
  }, [loadStatus])

  const start = async () => {
    setActionLoading(true)
    try {
      await api.get('/scheduler/start')
      await loadStatus()
    } finally {
      setActionLoading(false)
    }
  }

  const stop = async () => {
    setActionLoading(true)
    try {
      await api.get('/scheduler/stop')
      await loadStatus()
    } finally {
      setActionLoading(false)
    }
  }

  const sendAlert = async () => {
    setAlertLoading(true)
    setAlertResult(null)
    try {
      const res = await api.get('/send-alert')
      const data = res.data
      setAlertResult(
        data.best_trade
          ? `✅ Alert sent: ${data.best_trade.pair} ${data.best_trade.direction} (${data.best_trade.confidence}%)`
          : `ℹ️ ${data.message || 'No setup found'}`,
      )
    } catch (e: any) {
      setAlertResult(`❌ ${e?.message || 'Error sending alert'}`)
    } finally {
      setAlertLoading(false)
    }
  }

  return (
    <div className="glass-card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-white">Signal Scheduler</p>
        {status && (
          <span className={`text-xs font-mono font-bold px-2 py-1 rounded border ${
            status.running
              ? 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30'
              : 'text-zinc-500 bg-zinc-800 border-zinc-700'
          }`}>
            {status.running ? 'RUNNING' : 'STOPPED'}
          </span>
        )}
      </div>

      {status && (
        <p className="text-xs text-zinc-500 font-mono">
          Refresh every {status.interval_minutes}m · Filters: 80%+ confidence, RR ≥ 1.5
        </p>
      )}

      <div className="flex gap-2 flex-wrap">
        {status?.running ? (
          <button onClick={stop} disabled={actionLoading} className="btn-danger flex items-center gap-1.5">
            {actionLoading ? '...' : 'Stop Scheduler'}
          </button>
        ) : (
          <button onClick={start} disabled={actionLoading} className="btn-primary flex items-center gap-1.5">
            {actionLoading ? '...' : 'Start Scheduler'}
          </button>
        )}
        <button
          onClick={sendAlert}
          disabled={alertLoading}
          className="px-4 py-2 rounded-lg text-sm font-medium border transition-all
                     bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border-sky-500/30 hover:border-sky-400/60
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {alertLoading ? 'Sending...' : 'Send Telegram Alert'}
        </button>
      </div>

      {alertResult && (
        <p className="text-xs font-mono text-zinc-300 bg-zinc-800/60 rounded p-2">{alertResult}</p>
      )}
    </div>
  )
}
