import { useState, useEffect } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'

interface Props {
  onMenuToggle: () => void
}

export default function Navbar({ onMenuToggle }: Props) {
  const [time, setTime] = useState(new Date())
  const { connected } = useWebSocket({ path: '/ws/signals' })

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const formatTime = (d: Date) =>
    d.toUTCString().replace('GMT', 'UTC').slice(5)

  return (
    <header className="h-14 bg-zinc-950 border-b border-zinc-800/60 flex items-center px-5 gap-4 flex-shrink-0">
      {/* Hamburger */}
      <button
        onClick={onMenuToggle}
        className="text-zinc-400 hover:text-white transition-colors"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      <div className="flex-1" />

      {/* WS status */}
      <div className="flex items-center gap-1.5">
        <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
        <span className={`text-xs font-mono ${connected ? 'text-emerald-400' : 'text-red-400'}`}>
          {connected ? 'LIVE' : 'OFFLINE'}
        </span>
      </div>

      {/* Clock */}
      <div className="text-xs font-mono text-zinc-500 border border-zinc-800 rounded px-2.5 py-1">
        {formatTime(time)}
      </div>

      {/* Market Sessions */}
      <div className="hidden md:flex items-center gap-2 text-xs font-mono">
        {(['LONDON', 'NY', 'TOKYO'] as const).map((session) => (
          <span key={session} className="text-zinc-600 border border-zinc-800 rounded px-2 py-1">
            {session}
          </span>
        ))}
      </div>
    </header>
  )
}
