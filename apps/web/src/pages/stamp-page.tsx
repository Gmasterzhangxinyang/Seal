import { useState, useEffect, useCallback } from 'react'
import { CameraFeed } from '@/components/camera/camera-feed'
import { usePendingStamps } from '@/hooks/use-pending-stamps'
import { apiFetch, apiPost } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import type { StampResult, CameraListResponse, LeaveVerificationResult } from '@/types/api'

export function StampPage() {
  const { items: pendingItems, refresh: refreshPending } = usePendingStamps()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<StampResult | null>(null)
  const [cameras, setCameras] = useState<CameraListResponse | null>(null)
  const [camerasLoading, setCamerasLoading] = useState(true)
  const [switching, setSwitching] = useState(false)
  const [stampMode, setStampMode] = useState<'general' | 'leave'>('general')

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
      setResult({
        status: 'error',
        message: err instanceof Error ? err.message : '未知错误',
      })
    } finally {
      setLoading(false)
    }
  }

  const triggerLeaveStamp = async () => {
    setLoading(true)
    setResult(null)
    try {
      const data = await apiPost<LeaveVerificationResult>('/stamp/leave')
      if (data.success) {
        setResult({ status: 'approved', message: '验证通过，已盖章', fields: {} })
      } else if (data.decision === 'REVIEW') {
        setResult({
          status: 'pending_review',
          message: '验证不确定，已进入人工复审',
          warnings: data.warnings,
          fields: {},
        })
      } else {
        setResult({ status: 'rejected', errors: data.errors, warnings: data.warnings, fields: {} })
      }
    } catch (err) {
      setResult({ status: 'error', message: err instanceof Error ? err.message : '未知错误' })
    } finally {
      setLoading(false)
    }
  }

  const triggerStamp = () => {
    if (stampMode === 'leave') {
      triggerLeaveStamp()
    } else {
      triggerGeneralStamp()
    }
  }

  const triggerReviewStamp = async (reviewId: number) => {
    try {
      const data = await apiPost<StampResult>(`/review/${reviewId}/stamp`)
      setResult(data)
      if (data.status === 'approved') {
        setTimeout(refreshPending, 2000)
      }
    } catch (err) {
      setResult({
        status: 'error',
        message: err instanceof Error ? err.message : '未知错误',
      })
    }
  }

  return (
    <div className="text-center py-4">
      {/* 待盖章通知 */}
      {pendingItems.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4 mb-4 text-left">
          <h3 className="text-sm font-bold text-yellow-800 mb-2">有复审通过的文件待盖章</h3>
          <p className="text-xs text-yellow-700 mb-3">
            请将原文件放置在底板上，然后点击对应项目的"验证并盖章"按钮。
          </p>
          <ul className="space-y-2">
            {pendingItems.map((item) => (
              <li
                key={item.id}
                className="flex items-center justify-between py-2 border-b border-yellow-200 last:border-0 text-sm"
              >
                <span>
                  #{item.id} · {item.doc_type_name} · {item.operator_id} · {item.timestamp}
                </span>
                <button
                  onClick={() => triggerReviewStamp(item.id)}
                  className="px-3 py-1 bg-green-600 text-white rounded text-xs font-semibold hover:opacity-90"
                >
                  验证并盖章
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 摄像头预览 */}
      <div className="inline-block relative mb-4 rounded-xl overflow-hidden shadow-lg">
        <CameraFeed className="w-[480px] max-w-full" />
        {switching && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/40 rounded-lg z-20 gap-2">
            <div className="w-8 h-8 border-4 border-white/30 border-t-white rounded-full animate-spin" />
            <p className="text-white text-sm">正在切换摄像头...</p>
          </div>
        )}
        <div className="absolute top-2.5 right-2.5 z-10">
          {camerasLoading ? (
            <div className="px-2 py-1 rounded text-xs bg-black/60 text-white/70 flex items-center gap-1">
              <div className="w-3 h-3 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              检测摄像头...
            </div>
          ) : cameras && cameras.cameras.length > 1 ? (
            <select
              value={cameras.current}
              onChange={(e) => switchCamera(Number(e.target.value))}
              disabled={switching}
              className="px-2 py-1 rounded text-xs bg-black/60 text-white border-none outline-none cursor-pointer disabled:opacity-50"
            >
              {cameras.cameras.map((c) => (
                <option key={c.index} value={c.index}>
                  Cam {c.index} ({c.resolution})
                </option>
              ))}
            </select>
          ) : null}
        </div>
      </div>

      {/* 盖章模式切换 */}
      <div className="mb-4 flex items-center justify-center gap-4">
        <span className="text-sm text-gray-500">盖章模式：</span>
        <div className="flex rounded-lg border overflow-hidden">
          <button
            onClick={() => setStampMode('general')}
            className={cn(
              'px-4 py-1.5 text-sm font-medium transition',
              stampMode === 'general'
                ? 'bg-[#457b9d] text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50',
            )}
          >
            通用文档
          </button>
          <button
            onClick={() => setStampMode('leave')}
            className={cn(
              'px-4 py-1.5 text-sm font-medium transition',
              stampMode === 'leave'
                ? 'bg-[#457b9d] text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50',
            )}
          >
            请假条核验
          </button>
        </div>
      </div>

      {/* 盖章按钮 */}
      <div className="mb-4">
        <button
          onClick={triggerStamp}
          disabled={loading}
          className={cn(
            'w-40 h-40 rounded-full text-white font-bold text-lg leading-snug border-none cursor-pointer transition-all',
            'bg-gradient-to-br from-[#457b9d] to-[#1d3557] shadow-lg',
            'hover:scale-105 hover:shadow-xl active:scale-95',
            'disabled:bg-gray-400 disabled:cursor-not-allowed disabled:shadow-none disabled:scale-100',
          )}
        >
          {stampMode === 'leave' ? '扫描请假条\n并核验盖章' : '扫描\n&\n盖章'}
        </button>
      </div>

      {/* 结果展示 */}
      <div className="min-h-[70px] flex items-center justify-center">
        {!result && !loading && (
          <span className="text-gray-400 text-sm">将文件放入摄像头视野后点击按钮</span>
        )}
        {loading && (
          <div className="w-9 h-9 border-4 border-gray-200 border-t-[#457b9d] rounded-full animate-spin" />
        )}
        {result && <ResultCard result={result} />}
      </div>
    </div>
  )
}

function ResultCard({ result }: { result: StampResult }) {
  const styles: Record<string, string> = {
    approved: 'bg-green-50 border-l-4 border-green-500',
    rejected: 'bg-red-50 border-l-4 border-red-500',
    pending_review: 'bg-yellow-50 border-l-4 border-yellow-500',
    error: 'bg-red-50 border-l-4 border-gray-500',
  }
  const titles: Record<string, string> = {
    approved: '盖章完成',
    rejected: '未盖章',
    pending_review: '已推入复审队列',
    error: '系统错误',
  }
  const msgs = result.errors?.length
    ? result.errors
    : result.warnings?.length
      ? result.warnings
      : result.message
        ? [result.message]
        : []

  return (
    <div
      className={cn(
        'rounded-lg p-4 max-w-[480px] w-full text-left animate-in fade-in slide-in-from-bottom-2',
        styles[result.status] || styles.error,
      )}
    >
      <h3 className="font-bold text-sm mb-1">{titles[result.status] || '系统错误'}</h3>
      {msgs.length > 0 && (
        <ul className="list-disc pl-4 text-sm space-y-0.5">
          {msgs.map((m, i) => (
            <li key={i}>{m}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
