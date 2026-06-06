import { useEffect, useRef, useState, useCallback } from 'react'
import { WS_URL } from '../services/api'

interface UseWebSocketOptions {
  path: string
  onMessage?: (data: unknown) => void
  reconnectDelay?: number
}

export function useWebSocket({ path, onMessage, reconnectDelay = 3000 }: UseWebSocketOptions) {
  const [connected, setConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<unknown>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return

    const url = `${WS_URL}${path}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      setConnected(true)
    }

    ws.onmessage = (event) => {
      if (!mountedRef.current) return
      try {
        const data = JSON.parse(event.data)
        setLastMessage(data)
        onMessage?.(data)
      } catch {
        // non-JSON message
      }
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      setConnected(false)
      // Auto-reconnect
      reconnectTimer.current = setTimeout(() => {
        if (mountedRef.current) connect()
      }, reconnectDelay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [path, onMessage, reconnectDelay])

  useEffect(() => {
    mountedRef.current = true
    connect()

    return () => {
      mountedRef.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { connected, lastMessage, send }
}
