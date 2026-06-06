import { useState } from 'react'
import { motion } from 'framer-motion'
import { login } from '../services/api'

interface Props {
  onLogin: (token: string) => void
}

export default function Login({ onLogin }: Props) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username || !password) {
      setError('Please enter credentials')
      return
    }
    setLoading(true)
    setError('')
    try {
      const data = await login(username, password)
      onLogin(data.token)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-5"
        style={{
          backgroundImage: 'linear-gradient(#00ff88 1px, transparent 1px), linear-gradient(90deg, #00ff88 1px, transparent 1px)',
          backgroundSize: '60px 60px',
        }}
      />

      {/* Glow orb */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />

      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md relative"
      >
        {/* Card */}
        <div className="glass-card p-8 neon-border-green">
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 mb-4">
              <svg className="w-7 h-7 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-white">ForexAI</h1>
            <p className="text-zinc-500 text-sm mt-1 font-mono">Institutional Trading System</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs text-zinc-500 font-mono uppercase tracking-wider block mb-1.5">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                className="input-field"
                autoComplete="username"
              />
            </div>

            <div>
              <label className="text-xs text-zinc-500 font-mono uppercase tracking-wider block mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="input-field"
                autoComplete="current-password"
              />
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-2 text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg p-3 text-sm font-mono"
              >
                <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {error}
              </motion.div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border border-emerald-500/40
                         hover:border-emerald-400/60 rounded-lg font-semibold font-mono transition-all duration-200
                         disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
                  Authenticating...
                </>
              ) : (
                'Access Terminal'
              )}
            </button>
          </form>

          <p className="text-center text-xs text-zinc-700 font-mono mt-6">
            SECURED · ENCRYPTED · INSTITUTIONAL
          </p>
        </div>
      </motion.div>
    </div>
  )
}
