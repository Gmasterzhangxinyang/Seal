import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '@/lib/api-client'
import type { PendingStampItem } from '@/types/api'

export function usePendingStamps(intervalMs = 5000) {
  const [items, setItems] = useState<PendingStampItem[]>([])

  const refresh = useCallback(async () => {
    try {
      const data = await apiFetch<{ items: PendingStampItem[] }>('/review/pending_stamps')
      setItems(data.items)
    } catch {
      /* network error */
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh()
    const id = setInterval(refresh, intervalMs)
    return () => clearInterval(id)
  }, [refresh, intervalMs])

  return { items, refresh }
}
