import { motion } from 'framer-motion'
import { AIAnalysisData } from '../services/api'

interface Props {
  data: AIAnalysisData
}

function AnalysisBlock({ title, content, color }: { title: string; content: string; color: string }) {
  const colors: Record<string, string> = {
    blue: 'border-blue-500/30 bg-blue-500/5',
    emerald: 'border-emerald-500/30 bg-emerald-500/5',
    purple: 'border-purple-500/30 bg-purple-500/5',
    yellow: 'border-yellow-500/30 bg-yellow-500/5',
    red: 'border-red-500/30 bg-red-500/5',
  }
  const textColors: Record<string, string> = {
    blue: 'text-blue-400',
    emerald: 'text-emerald-400',
    purple: 'text-purple-400',
    yellow: 'text-yellow-400',
    red: 'text-red-400',
  }

  return (
    <div className={`border rounded-xl p-4 ${colors[color]}`}>
      <p className={`text-xs font-mono font-bold uppercase tracking-widest mb-2 ${textColors[color]}`}>
        {title}
      </p>
      <p className="text-sm text-zinc-300 font-mono leading-relaxed whitespace-pre-wrap break-words">
        {content || 'No data available'}
      </p>
    </div>
  )
}

export default function AIAnalysis({ data }: Props) {
  const prob = data.ai_probability ?? null

  return (
    <div className="space-y-4">
      {/* Header with probability */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <p className="text-xs text-zinc-500 font-mono uppercase tracking-widest mb-1">AI Engine</p>
            <p className="text-2xl font-bold text-white">CrewAI Analysis</p>
          </div>
          {prob !== null && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="flex flex-col items-center"
            >
              <div
                className="relative w-24 h-24"
                style={{
                  background: `conic-gradient(#00ff88 ${prob * 3.6}deg, #27272a ${prob * 3.6}deg)`,
                  borderRadius: '50%',
                }}
              >
                <div className="absolute inset-2 bg-zinc-950 rounded-full flex items-center justify-center">
                  <span className="text-xl font-bold font-mono text-emerald-400">{prob}%</span>
                </div>
              </div>
              <p className="text-xs text-zinc-500 font-mono mt-1">AI Probability</p>
            </motion.div>
          )}
        </div>
        {data.warning && (
          <div className="mt-3 flex items-start gap-2 text-yellow-400 bg-yellow-400/5 border border-yellow-400/20 rounded-lg p-3">
            <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <p className="text-xs font-mono">{data.warning}</p>
          </div>
        )}
      </div>

      {/* Analysis blocks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <AnalysisBlock title="BOS Analysis" content={data.bos_analysis} color="blue" />
        <AnalysisBlock title="CHOCH Analysis" content={data.choch_analysis} color="purple" />
        <AnalysisBlock title="Liquidity Sweeps" content={data.liquidity_sweeps} color="yellow" />
        <AnalysisBlock title="Session Analysis" content={data.session_analysis} color="emerald" />
      </div>

      {data.analysis && (
        <AnalysisBlock title="Full AI Analysis" content={data.analysis} color="blue" />
      )}
    </div>
  )
}
