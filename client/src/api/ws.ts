import { useEffect, useRef, useState } from 'react'
import type { ProgressEvent, RunStatus } from '../types'

const TERMINAL: RunStatus[] = ['completed', 'failed', 'cancelled']

/** Subscribe to live progress events for a run via WebSocket. */
export function useRunProgress(runId: string, onFinal?: () => void) {
  const [event, setEvent] = useState<ProgressEvent | null>(null)
  const [connected, setConnected] = useState(false)
  const finalCb = useRef(onFinal)
  finalCb.current = onFinal

  useEffect(() => {
    const API_BASE = import.meta.env.VITE_API_URL
    let ws: WebSocket | null = null
    try {
      if (API_BASE) {
        const wsUrl = API_BASE.replace(/^http/, 'ws')
        ws = new WebSocket(`${wsUrl}/ws/${runId}`)
      } else {
        const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
        ws = new WebSocket(`${proto}://${window.location.host}/ws/${runId}`)
      }
    } catch {
      return
    }
    ws.onopen = () => setConnected(true)
    ws.onmessage = (m) => {
      try {
        const ev = JSON.parse(m.data) as ProgressEvent
        setEvent(ev)
        if (TERMINAL.includes(ev.status)) {
          finalCb.current?.()
          ws?.close()
        }
      } catch {
        /* ignore malformed frames */
      }
    }
    ws.onclose = () => setConnected(false)
    ws.onerror = () => setConnected(false)
    return () => {
      ws?.close()
    }
  }, [runId])

  return { event, connected }
}
