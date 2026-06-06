import { useEffect, useState } from 'react'
import api from '../services/api'

export default function BackendStatus() {
  const [status, setStatus] = useState<'checking' | 'online' | 'offline'>('checking')
  const [error, setError] = useState('')

  const check = async () => {
    try {
      await api.get('/dashboard', { timeout: 4000 })
      setStatus('online')
      setError('')
    } catch (e: any) {
      setStatus('offline')
      if (e.code === 'ERR_NETWORK' || e.code === 'ECONNREFUSED') {
        setError('Cannot reach backend — is FastAPI running on port 8000?')
      } else if (e.response?.status === 401) {
        setStatus('online') // reachable, just auth required
        setError('')
      } else {
        setError(e.message || 'Backend unreachable')
      }
    }
  }

  useEffect(() => {
    check()
    const t = setInterval(check, 10000)
    return () => clearInterval(t)
  }, [])

  if (status === 'checking' || status === 'online') return null

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm">
      <div className="bg-red-950 border border-red-500/40 rounded-xl p-4 shadow-2xl">
        <div className="flex items-start gap-3">
          <div className="w-2 h-2 mt-1.5 rounded-full bg-red-400 animate-pulse flex-shrink-0" />
          <div className="flex-1">
            <p className="text-red-400 font-semibold text-sm">Backend Offline</p>
            <p className="text-red-300/70 text-xs mt-1 font-mono">{error}</p>
            <p className="text-zinc-500 text-xs mt-2 font-mono">
              Run: <span className="text-zinc-300">uvicorn app.main:app --reload</span>
            </p>
          </div>
          <button onClick={check} className="text-zinc-500 hover:text-white ml-1 mt-0.5">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
