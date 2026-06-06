import { useEffect, useState, useCallback } from 'react'
import { fetchSettings, saveSettings, SettingsData } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

export default function Settings() {
  const [form, setForm] = useState<SettingsData>({
    oanda_api_key: '',
    telegram_bot_token: '',
    telegram_chat_id: '',
    risk_percentage: 1,
    max_daily_loss: 3,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const load = useCallback(async () => {
    try {
      const data = await fetchSettings()
      setForm(data)
      setError('')
    } catch (e: any) {
      setError(e?.message || 'Failed to load settings')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      await saveSettings(form)
      setSuccess('Settings saved successfully')
      setTimeout(() => setSuccess(''), 3000)
    } catch (e: any) {
      setError(e?.message || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const set = (key: keyof SettingsData, val: string | number) =>
    setForm((prev) => ({ ...prev, [key]: val }))

  if (loading) return <LoadingSpinner size="lg" text="Loading settings..." />

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-zinc-500 text-sm font-mono mt-0.5">Configure your trading system</p>
      </div>

      {error && <ErrorMessage message={error} />}
      {success && (
        <div className="flex items-center gap-2 text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 rounded-lg p-3 text-sm font-mono">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          {success}
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-5">
        {/* OANDA */}
        <div className="glass-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-blue-400" />
            OANDA API
          </h2>
          <div>
            <label className="text-xs text-zinc-500 font-mono uppercase tracking-wider block mb-1.5">
              API Key
            </label>
            <input
              type="password"
              value={form.oanda_api_key}
              onChange={(e) => set('oanda_api_key', e.target.value)}
              placeholder="Your OANDA API key"
              className="input-field"
            />
          </div>
        </div>

        {/* Telegram */}
        <div className="glass-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-sky-400" />
            Telegram Bot
          </h2>
          <div>
            <label className="text-xs text-zinc-500 font-mono uppercase tracking-wider block mb-1.5">
              Bot Token
            </label>
            <input
              type="password"
              value={form.telegram_bot_token}
              onChange={(e) => set('telegram_bot_token', e.target.value)}
              placeholder="123456:ABC-DEF..."
              className="input-field"
            />
          </div>
          <div>
            <label className="text-xs text-zinc-500 font-mono uppercase tracking-wider block mb-1.5">
              Chat ID
            </label>
            <input
              type="text"
              value={form.telegram_chat_id}
              onChange={(e) => set('telegram_chat_id', e.target.value)}
              placeholder="-100123456789"
              className="input-field"
            />
          </div>
        </div>

        {/* Risk */}
        <div className="glass-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-yellow-400" />
            Risk Management
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-zinc-500 font-mono uppercase tracking-wider block mb-1.5">
                Risk Per Trade (%)
              </label>
              <input
                type="number"
                min={0.1}
                max={10}
                step={0.1}
                value={form.risk_percentage}
                onChange={(e) => set('risk_percentage', Number(e.target.value))}
                className="input-field"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-500 font-mono uppercase tracking-wider block mb-1.5">
                Max Daily Loss (%)
              </label>
              <input
                type="number"
                min={0.1}
                max={20}
                step={0.1}
                value={form.max_daily_loss}
                onChange={(e) => set('max_daily_loss', Number(e.target.value))}
                className="input-field"
              />
            </div>
          </div>

          {/* Risk sliders */}
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <span className="text-zinc-600">Risk per trade</span>
                <span className="text-yellow-400">{form.risk_percentage}%</span>
              </div>
              <input
                type="range"
                min={0.1}
                max={5}
                step={0.1}
                value={form.risk_percentage}
                onChange={(e) => set('risk_percentage', Number(e.target.value))}
                className="w-full accent-yellow-400"
              />
            </div>
            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <span className="text-zinc-600">Max daily loss</span>
                <span className="text-red-400">{form.max_daily_loss}%</span>
              </div>
              <input
                type="range"
                min={0.5}
                max={10}
                step={0.5}
                value={form.max_daily_loss}
                onChange={(e) => set('max_daily_loss', Number(e.target.value))}
                className="w-full accent-red-400"
              />
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full py-3 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border border-emerald-500/40
                     rounded-lg font-semibold font-mono transition-all duration-200
                     disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {saving ? (
            <>
              <div className="w-4 h-4 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
              Saving...
            </>
          ) : (
            'Save Settings'
          )}
        </button>
      </form>
    </div>
  )
}
