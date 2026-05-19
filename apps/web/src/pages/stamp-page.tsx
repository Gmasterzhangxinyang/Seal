import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { CameraFeed } from '@/components/camera/camera-feed'
import { VoiceControl } from '@/components/voice-control'
import { usePendingStamps } from '@/hooks/use-pending-stamps'
import { apiFetch, apiPost } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import type { StampResult, CameraListResponse } from '@/types/api'

export function StampPage() {
  const { items: pendingItems, refresh: refreshPending } = usePendingStamps()
  const { t } = useTranslation('stamp')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<StampResult | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [cameras, setCameras] = useState<CameraListResponse | null>(null)
  const [camerasLoading, setCamerasLoading] = useState(true)
  const [switching, setSwitching] = useState(false)
  const [stampMode, setStampMode] = useState('general')

  useEffect(() => {
    apiFetch<CameraListResponse>('/cameras')
      .then(setCameras)
      .catch(() => {})
      .finally(() => setCamerasLoading(false))
  }, [])

  const switchCamera = useCallback(async (index: number) => {
    setSwitching(true)
    try {
      await apiPost('/cameras/select', { index })
      apiFetch<CameraListResponse>('/cameras').then(setCameras)
    } finally {
      setTimeout(() => setSwitching(false), 1000)
    }
  }, [])

  const triggerGeneralStamp = async () => {
    setLoading(true)
    setResult(null)
    try {
      const data = await apiPost<StampResult>('/stamp')
      setResult(data)
      if (data.status === 'approved' || data.status === 'pending_review') {
        setTimeout(refreshPending, 2000)
      }
    } catch (err) {
      setResult({ status: 'error', message: err instanceof Error ? err.message : t('systemError') })
    } finally {
      setLoading(false)
    }
  }

  const triggerLeaveStamp = async () => {
    setLoading(true)
    setResult(null)
    setLogs([])
    try {
      const res = await fetch('/api/stamp/leave', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (currentEvent === 'log') {
              setLogs((prev) => [...prev, data])
            } else if (currentEvent === 'result') {
              const r = JSON.parse(data)
              if (r.success) {
                setResult({ status: 'approved', message: t('verificationPassed'), fields: {} })
              } else if (r.decision === 'REVIEW') {
                setResult({ status: 'pending_review', message: t('verificationUncertain'), warnings: r.warnings, fields: {} })
              } else {
                setResult({ status: 'rejected', errors: r.errors, warnings: r.warnings, fields: {} })
              }
            }
          }
        }
      }
    } catch (err) {
      setResult({ status: 'error', message: err instanceof Error ? err.message : t('systemError') })
    } finally {
      setLoading(false)
    }
  }

  const triggerStamp = () => {
    stampMode === 'leave' ? triggerLeaveStamp() : triggerGeneralStamp()
  }

  const triggerReviewStamp = async (reviewId: number) => {
    try {
      const data = await apiPost<StampResult>(`/review/${reviewId}/stamp`)
      setResult(data)
      if (data.status === 'approved') setTimeout(refreshPending, 2000)
    } catch (err) {
      setResult({ status: 'error', message: err instanceof Error ? err.message : t('systemError') })
    }
  }

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-full">
      {/* Left: Camera */}
      <div className="flex-1 flex flex-col items-center justify-start min-w-0">
        {pendingItems.length > 0 && (
          <div className="w-full max-w-[600px] bg-warning/10 border border-warning/30 rounded-lg p-4 mb-4 animate-slide-up">
            <h3 className="text-sm font-semibold text-foreground mb-1">{t('pendingStampTitle')}</h3>
            <p className="text-xs text-muted-foreground mb-3">{t('pendingStampDesc')}</p>
            <ul className="space-y-2">
              {pendingItems.map((item) => (
                <li key={item.id} className="flex items-center justify-between py-1.5 border-b border-border last:border-0 text-sm">
                  <span className="text-muted-foreground">
                    <span className="font-mono text-xs">#{item.id}</span> · {item.doc_type_name} · {item.operator_id}
                  </span>
                  <Button size="sm" onClick={() => triggerReviewStamp(item.id)}>
                    {t('verifyAndStamp')}
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="relative inline-block w-full max-w-[600px]">
          <CameraFeed className="w-full" />
          {switching && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-foreground/30 rounded-lg z-20 gap-2">
              <Spinner className="h-7 w-7 border-muted-foreground/30 border-t-white" />
              <p className="text-white text-xs">{t('switchingCamera')}</p>
            </div>
          )}
          <div className="absolute top-2 right-2 z-20">
            {camerasLoading ? (
              <div className="px-2 py-1 rounded-md text-xs bg-foreground/50 text-white/70 flex items-center gap-1.5">
                <Spinner className="h-3 w-3 border-white/30 border-t-white" />
                {t('detectingCamera')}
              </div>
            ) : cameras ? (
              cameras.cameras.length > 1 ? (
                <select
                  value={cameras.current}
                  onChange={(e) => switchCamera(Number(e.target.value))}
                  disabled={switching}
                  className="px-2 py-1 rounded-md text-xs bg-foreground/50 text-white border-0 outline-none cursor-pointer disabled:opacity-50"
                >
                  {cameras.cameras.map((c) => (
                    <option key={c.index} value={c.index}>
                      Cam {c.index} ({c.resolution})
                    </option>
                  ))}
                </select>
              ) : (
                <span className="px-2 py-1 rounded-md text-xs bg-foreground/50 text-white/70">
                  Cam {cameras.current}
                </span>
              )
            ) : null}
          </div>
        </div>

        {logs.length > 0 && (
          <div className="w-full max-w-[600px] mt-4">
            <div className="bg-foreground rounded-lg p-3 text-left font-mono text-xs max-h-[180px] overflow-y-auto">
              {logs.map((log, i) => (
                <div key={i} className={cn('py-0.5', i === logs.length - 1 && loading ? 'text-green-400' : 'text-muted-foreground')}>
                  <span className="text-muted-foreground/50 mr-2">{String(i + 1).padStart(2, '0')}</span>
                  {log}
                </div>
              ))}
              {loading && <span className="inline-block w-2 h-3 bg-green-400 animate-pulse ml-1" />}
            </div>
          </div>
        )}
      </div>

      {/* Right: Controls */}
      <div className="lg:w-[280px] shrink-0 flex flex-col items-center gap-6">
        {/* Mode toggle */}
        <Tabs value={stampMode} onValueChange={setStampMode}>
          <TabsList>
            <TabsTrigger value="general">{t('generalDoc')}</TabsTrigger>
            <TabsTrigger value="leave">{t('leaveVerification')}</TabsTrigger>
          </TabsList>
          <TabsContent value="general" />
          <TabsContent value="leave" />
        </Tabs>

        {/* Stamp button */}
        <button
          onClick={triggerStamp}
          disabled={loading}
          className={cn(
            'w-36 h-36 rounded-full text-primary-foreground font-bold text-base leading-snug border-none cursor-pointer transition-all duration-200 ease-out',
            'bg-primary shadow-sm hover:shadow-md active:scale-95',
            'disabled:bg-muted-foreground/30 disabled:cursor-not-allowed disabled:shadow-none disabled:scale-100 disabled:text-muted-foreground',
          )}
        >
          {stampMode === 'leave' ? t('scanLeaveAndStamp') : t('scanAndStamp')}
        </button>

        {/* Voice control */}
        <VoiceControl />

        {/* Result */}
        <div className="min-h-[60px] flex items-center justify-center w-full">
          {!result && !loading && (
            <span className="text-muted-foreground text-sm">{t('placeDocInCamera')}</span>
          )}
          {loading && <Spinner className="h-8 w-8" />}
          {result && <ResultCard result={result} />}
        </div>
      </div>
    </div>
  )
}

function ResultCard({ result }: { result: StampResult }) {
  const { t } = useTranslation('stamp')

  const variantMap: Record<string, 'success' | 'destructive' | 'warning' | 'default'> = {
    approved: 'success',
    rejected: 'destructive',
    pending_review: 'warning',
    error: 'destructive',
  }
  const titleMap: Record<string, string> = {
    approved: t('stampComplete'),
    rejected: t('notStamped'),
    pending_review: t('pushedToReview'),
    error: t('systemError'),
  }
  const msgs = result.errors?.length
    ? result.errors
    : result.warnings?.length
      ? result.warnings
      : result.message ? [result.message] : []

  return (
    <div className="w-full max-w-[280px] animate-slide-up">
      <Badge variant={variantMap[result.status] || 'default'} className="mb-2">
        {titleMap[result.status] || t('systemError')}
      </Badge>
      {msgs.length > 0 && (
        <ul className="text-sm text-muted-foreground space-y-0.5">
          {msgs.map((m, i) => <li key={i}>{m}</li>)}
        </ul>
      )}
    </div>
  )
}
