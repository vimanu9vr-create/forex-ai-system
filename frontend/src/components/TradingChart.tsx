import { useEffect, useRef, useState } from 'react'

const PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'NZDUSD', 'USDCHF', 'XAUUSD']

export default function TradingChart() {
  const containerRef = useRef<HTMLDivElement>(null)
  const widgetRef = useRef<HTMLDivElement>(null)
  const [symbol, setSymbol] = useState('EURUSD')
  const [interval, setInterval] = useState('60')

  useEffect(() => {
    if (!containerRef.current) return

    // Remove old widget
    if (widgetRef.current) {
      widgetRef.current.innerHTML = ''
    }

    const script = document.createElement('script')
    script.src = 'https://s3.tradingview.com/tv.js'
    script.async = true
    script.onload = () => {
      if (!widgetRef.current) return
      // @ts-ignore
      new window.TradingView.widget({
        symbol: `FX:${symbol}`,
        interval,
        timezone: 'Etc/UTC',
        theme: 'dark',
        style: '1',
        locale: 'en',
        toolbar_bg: '#09090b',
        enable_publishing: false,
        hide_top_toolbar: false,
        hide_legend: false,
        save_image: false,
        container_id: 'tv-chart-container',
        autosize: true,
        studies: ['MASimple@tv-studioid', 'RSI@tv-studioid'],
        overrides: {
          'paneProperties.background': '#09090b',
          'paneProperties.backgroundType': 'solid',
          'scalesProperties.textColor': '#71717a',
          'mainSeriesProperties.candleStyle.upColor': '#00ff88',
          'mainSeriesProperties.candleStyle.downColor': '#ff4466',
          'mainSeriesProperties.candleStyle.borderUpColor': '#00ff88',
          'mainSeriesProperties.candleStyle.borderDownColor': '#ff4466',
          'mainSeriesProperties.candleStyle.wickUpColor': '#00ff88',
          'mainSeriesProperties.candleStyle.wickDownColor': '#ff4466',
        },
      })
    }

    // Clear and re-add
    if (widgetRef.current) {
      widgetRef.current.id = 'tv-chart-container'
      document.head.appendChild(script)
    }

    return () => {
      if (script.parentNode) script.parentNode.removeChild(script)
    }
  }, [symbol, interval])

  return (
    <div className="glass-card overflow-hidden">
      {/* Controls */}
      <div className="px-5 py-3 border-b border-zinc-800/60 flex items-center gap-3 flex-wrap">
        <p className="text-sm font-semibold text-white">Live Chart</p>
        <div className="flex gap-1.5 flex-wrap">
          {PAIRS.map((p) => (
            <button
              key={p}
              onClick={() => setSymbol(p)}
              className={`px-2.5 py-1 rounded text-xs font-mono transition-all ${
                symbol === p
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  : 'text-zinc-500 border border-zinc-800 hover:text-zinc-300 hover:border-zinc-700'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <div className="flex gap-1.5">
          {[
            { v: '1', l: '1m' },
            { v: '5', l: '5m' },
            { v: '15', l: '15m' },
            { v: '60', l: '1H' },
            { v: '240', l: '4H' },
            { v: 'D', l: '1D' },
          ].map(({ v, l }) => (
            <button
              key={v}
              onClick={() => setInterval(v)}
              className={`px-2 py-1 rounded text-xs font-mono transition-all ${
                interval === v
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                  : 'text-zinc-500 border border-zinc-800 hover:text-zinc-300'
              }`}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      {/* Chart container */}
      <div ref={containerRef} className="h-[78vh] min-h-[560px] relative">
        <div ref={widgetRef} className="w-full h-full" />
        {/* Fallback if TV script fails */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-0 tv-fallback">
          <p className="text-zinc-600 text-sm font-mono">TradingView chart loading…</p>
        </div>
      </div>
    </div>
  )
}
