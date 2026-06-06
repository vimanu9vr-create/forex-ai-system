import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar'
import Navbar from './components/Navbar'
import BackendStatus from './components/BackendStatus'
import Dashboard from './pages/Dashboard'
import Signals from './pages/Signals'
import Analytics from './pages/Analytics'
import Trades from './pages/Trades'
import AIAnalysisPage from './pages/AIAnalysisPage'
import Settings from './pages/Settings'
import Login from './pages/Login'

function PrivateLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className="flex h-screen bg-black overflow-hidden">
      <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
      <div className="flex flex-col flex-1 min-w-0">
        <Navbar onMenuToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className="flex-1 overflow-y-auto custom-scroll p-6 bg-black">
          {children}
        </main>
      </div>
    </div>
  )
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('auth_token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('auth_token'))

  useEffect(() => {
    const onStorage = () => setToken(localStorage.getItem('auth_token'))
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  return (
    <>
      <Routes>
        <Route path="/login" element={<Login onLogin={(t) => { localStorage.setItem('auth_token', t); setToken(t) }} />} />
        <Route
          path="/*"
          element={
            <RequireAuth>
              <PrivateLayout>
                <Routes>
                  <Route index element={<Navigate to="/dashboard" replace />} />
                  <Route path="dashboard" element={<Dashboard />} />
                  <Route path="signals" element={<Signals />} />
                  <Route path="analytics" element={<Analytics />} />
                  <Route path="trades" element={<Trades />} />
                  <Route path="ai-analysis" element={<AIAnalysisPage />} />
                  <Route path="settings" element={<Settings />} />
                </Routes>
              </PrivateLayout>
            </RequireAuth>
          }
        />
      </Routes>
      <BackendStatus />
    </>
  )
}
