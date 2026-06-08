import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401; surface clear network error messages
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    if (err.code === 'ERR_NETWORK' || err.code === 'ECONNABORTED') {
      err.message = 'Network error — backend unreachable (port 8000)'
    }
    return Promise.reject(err)
  },
)

// ── Types ──────────────────────────────────────────────────────────────────

export interface DashboardData {
  bot_status: string
  total_trades: number
  win_rate: number
  total_pnl: number
  open_trades: number
  best_pair: string
  market_bias?: string
  winning_trades?: number
  losing_trades?: number
}

export interface Signal {
  pair: string
  signal: string
  entry: number
  stop_loss: number
  take_profit: number
  confluence_score: number
  setup?: string
  htf_aligned?: boolean
  // real scanner fields
  timeframe?: string
  model?: string
  session?: string
  risk_reward?: string | number
  bias?: string | Record<string, unknown>
  killzone?: unknown
  updated_at?: string
  // intraday (5m/15m liquidity-sweep) engine fields
  quality_score?: number
  entry_basis?: string
  swept_liquidity?: number
  mss_level?: number
  entry_type?: string
  current_price?: number
  distance_to_entry_pips?: number
  // top-down fields
  htf_bias?: string
  htf_daily?: string
  htf_4h?: string
  target_basis?: string
  runner_target?: number
  sweep_time?: string
  // professional layer (grade / management / freshness)
  grade?: string
  risk_pips?: number
  reward_pips?: number
  tp1?: number
  tp2?: number
  management?: string
  fresh?: boolean
  candle_age_min?: number
}

export interface Trade {
  id: number
  pair: string
  signal: string
  direction: string
  entry_price: number
  stop_loss: number
  take_profit: number
  pnl: string | number
  status: string
  opened_at: string
  closed_at: string | null
  probability_score: number
}

export interface AnalyticsData {
  total_trades: number
  buy_trades: number
  sell_trades: number
  open_trades: number
  closed_trades: number
  avg_probability: number
  pair_stats: { pair: string; trades: number }[]
}

export interface TelegramLogsData {
  logs: string[]
}

export interface AIAnalysisData {
  bos_analysis: string
  choch_analysis: string
  liquidity_sweeps: string
  session_analysis: string
  ai_probability: number | null
  analysis: string | null
  source: string
  warning: string | null
}

export interface SettingsData {
  oanda_api_key: string
  telegram_bot_token: string
  telegram_chat_id: string
  risk_percentage: number
  max_daily_loss: number
}

// ── API calls ──────────────────────────────────────────────────────────────

export const fetchDashboard = () =>
  api.get<DashboardData>('/dashboard').then((r) => r.data)

export const fetchSignals = () =>
  api.get<Signal[]>('/signals').then((r) => r.data)

// Top-down liquidity-sweep engine on the chosen entry TF ('5min' | '15min') and session
// ('london' | 'newyork' | 'both'). Maps quality_score -> confluence_score so it reuses
// SignalsTable unchanged. Longer timeout: a cold multi-pair scan can take ~50s.
export const fetchIntradaySignals = (tf: string = '15min', session: string = 'london') =>
  api
    .get<Signal[]>(
      `/signals/intraday?tf=${encodeURIComponent(tf)}&session=${encodeURIComponent(session)}`,
      { timeout: 90000 },
    )
    .then((r) =>
      (Array.isArray(r.data) ? r.data : []).map((s) => ({
        ...s,
        confluence_score: s.quality_score ?? s.confluence_score ?? 0,
      })),
    )

export interface IntradayVerdict {
  verdict: string
  confidence: number
  reason: string
  source?: string
  raw?: string
  warning?: string
}

// On-demand CrewAI desk verdict (TAKE/SKIP) on a specific 15m signal.
export const validateIntradaySignal = (signal: Signal) =>
  api.post<IntradayVerdict>('/signals/intraday/validate', signal, { timeout: 90000 }).then((r) => r.data)

export const fetchTradeHistory = (limit = 50) =>
  api.get<Trade[]>(`/trade-history?limit=${limit}`).then((r) => r.data)

export const fetchAnalytics = () =>
  api.get<AnalyticsData>('/analytics').then((r) => r.data)

export const fetchTelegramLogs = (limit = 50) =>
  api.get<TelegramLogsData>(`/telegram-logs?limit=${limit}`).then((r) => r.data)

export const fetchAIAnalysis = () =>
  api.get<AIAnalysisData>('/ai-analysis').then((r) => r.data)

export const fetchSettings = () =>
  api.get<SettingsData>('/settings').then((r) => r.data)

export const saveSettings = (data: SettingsData) =>
  api.post('/settings', data).then((r) => r.data)

export const login = (username: string, password: string) =>
  api.post<{ token: string; token_type: string }>('/auth/login', { username, password }).then((r) => r.data)

export const fetchPerformance = () =>
  api.get('/performance').then((r) => r.data)

export const executeSignalTrade = (payload: {
  pair: string
  signal: string
  entry: number
  stop_loss: number
  take_profit: number
  probability: number
  units?: number
}) => api.post('/trades/execute', payload).then((r) => r.data)

export const WS_URL =
  import.meta.env.VITE_WS_URL ||
  (typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    : 'ws://127.0.0.1:8000')

export default api
