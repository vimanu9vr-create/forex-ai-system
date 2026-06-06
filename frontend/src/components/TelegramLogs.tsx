import { useEffect, useRef } from 'react'

interface Props {
  logs: string[]
  loading?: boolean
}

export default function TelegramLogs({ logs, loading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const colorize = (line: string) => {
    if (line.includes('BUY')) return 'text-emerald-400'
    if (line.includes('SELL')) return 'text-red-400'
    if (line.includes('status=open')) return 'text-blue-400'
    if (line.includes('status=closed')) return 'text-zinc-500'
    return 'text-zinc-300'
  }

  return (
    <div className="glass-card overflow-hidden">
      {/* Terminal header */}
      <div className="px-4 py-3 border-b border-zinc-800/60 flex items-center gap-2">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-500/70" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
          <div className="w-3 h-3 rounded-full bg-emerald-500/70" />
        </div>
        <p className="text-xs font-mono text-zinc-500 ml-2">telegram-signal-logs.log</p>
        <div className="flex-1" />
        {loading && (
          <div className="w-3 h-3 border border-zinc-600 border-t-emerald-400 rounded-full animate-spin" />
        )}
        <span className="text-xs font-mono text-zinc-600">{logs.length} entries</span>
      </div>

      {/* Terminal body */}
      <div className="bg-black/40 h-[400px] overflow-y-auto custom-scroll font-mono text-xs p-4 space-y-1">
        {logs.length === 0 ? (
          <p className="text-zinc-700">No log entries yet...</p>
        ) : (
          logs.map((line, i) => (
            <div key={i} className="flex gap-2">
              <span className="text-zinc-700 select-none flex-shrink-0">{String(i + 1).padStart(3, '0')}</span>
              <span className={`${colorize(line)} break-all`}>{line}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Blinking cursor */}
      <div className="px-4 py-2 border-t border-zinc-800/60 flex items-center gap-2">
        <span className="text-emerald-400 font-mono text-xs">$</span>
        <span className="text-zinc-600 font-mono text-xs cursor-blink">_</span>
      </div>
    </div>
  )
}
