import { create } from 'zustand'

type ConnectionStatus = 'connected' | 'connecting' | 'disconnected'

interface ConnectionState {
  status: ConnectionStatus
  setStatus: (status: ConnectionStatus) => void
}

export const useConnectionStore = create<ConnectionState>((set) => ({
  status: 'connecting',
  setStatus: (status) => set({ status }),
}))

const POLL_INTERVAL = 1_000

export function startConnectionMonitor() {
  const { setStatus } = useConnectionStore.getState()

  async function check() {
    try {
      const res = await fetch('/api/auth/me', { credentials: 'include' })
      if (res.ok) {
        setStatus('connected')
      } else if (res.status === 401) {
        setStatus('connected')
      } else {
        setStatus('disconnected')
      }
    } catch {
      setStatus('disconnected')
    }
  }

  setStatus('connecting')
  check()
  return setInterval(check, POLL_INTERVAL)
}
