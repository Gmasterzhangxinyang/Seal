import { useEffect, useState } from 'react'
import { apiFetch, apiPost } from '@/lib/api-client'
import type { ReviewItem } from '@/types/api'

export function ReviewPage() {
  const [pending, setPending] = useState<ReviewItem[]>([])
  const [allItems, setAllItems] = useState<ReviewItem[]>([])
  const [tab, setTab] = useState<'pending' | 'all'>('pending')
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const refresh = async () => {
    setLoading(true)
    try {
      const [p, a] = await Promise.all([
        apiFetch<ReviewItem[]>('/review/pending'),
        apiFetch<ReviewItem[]>('/review/all'),
      ])
      setPending(p)
      setAllItems(a)
    } catch {
      /* network error */
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh()
  }, [])

  const handleResolve = async (id: number, decision: string) => {
    await apiPost(`/review/${id}/resolve`, { decision })
    refresh()
  }

  const items = tab === 'pending' ? pending : allItems

  const statusLabel: Record<string, string> = {
    pending: '待处理',
    approved: '已通过',
    rejected: '已拒绝',
    stamping: '待盖章',
  }
  const statusStyle: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    approved: 'bg-green-100 text-green-800',
    rejected: 'bg-red-100 text-red-800',
    stamping: 'bg-blue-100 text-blue-800',
  }

  const parseJson = (raw: string | null): Record<string, string> | null => {
    if (!raw) return null
    try {
      const obj = JSON.parse(raw)
      if (typeof obj === 'object' && obj !== null) return obj
      return null
    } catch {
      return null
    }
  }

  return (
    <div className="card bg-white rounded-xl shadow p-6">
      <h2 className="text-lg font-bold text-[#1d3557] mb-4">人工复审</h2>
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setTab('pending')}
          className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition ${tab === 'pending' ? 'bg-[#457b9d] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
        >
          待处理 ({pending.length})
        </button>
        <button
          onClick={() => setTab('all')}
          className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition ${tab === 'all' ? 'bg-[#457b9d] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
        >
          全部 ({allItems.length})
        </button>
      </div>

      {loading ? (
        <div className="text-center py-8 text-muted-foreground">加载中...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">暂无数据</div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const expanded = expandedId === item.id
            const fields = parseJson(item.doc_fields)
            return (
              <div key={item.id} className="border rounded-lg overflow-hidden">
                {/* 头部 */}
                <div
                  className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
                  onClick={() => setExpandedId(expanded ? null : item.id)}
                >
                  <div>
                    <span className="font-semibold">#{item.id}</span>
                    <span className="mx-2 text-gray-400">·</span>
                    <span>{item.doc_type_name}</span>
                    <span className="mx-2 text-gray-400">·</span>
                    <span className="text-sm text-gray-500">{item.operator_id}</span>
                    <span className="mx-2 text-gray-400">·</span>
                    <span className="text-sm text-gray-500">{item.timestamp}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs font-bold px-2 py-0.5 rounded ${statusStyle[item.status] || 'bg-gray-100'}`}
                    >
                      {statusLabel[item.status] || item.status}
                    </span>
                    <span className="text-xs text-[#457b9d]">{expanded ? '收起' : '展开'}</span>
                  </div>
                </div>

                {/* 展开详情 */}
                {expanded && (
                  <div className="px-4 pb-4 bg-gray-50 border-t">
                    <div className="grid grid-cols-2 gap-4 mt-3">
                      {/* 图片预览 */}
                      <div>
                        <p className="text-xs font-semibold text-gray-500 mb-2">文件图像</p>
                        {item.image_path ? (
                          <img
                            src={`/api/images/${item.image_path}`}
                            alt="复审文件"
                            className="w-full max-h-48 object-contain rounded border bg-white"
                          />
                        ) : (
                          <p className="text-xs text-gray-400">无图片</p>
                        )}
                      </div>
                      {/* OCR + 字段 */}
                      <div className="space-y-3">
                        {item.ocr_text && (
                          <div>
                            <p className="text-xs font-semibold text-gray-500 mb-1">OCR 识别结果</p>
                            <pre className="text-xs bg-white rounded border p-2 max-h-32 overflow-auto whitespace-pre-wrap">
                              {item.ocr_text}
                            </pre>
                          </div>
                        )}
                        {item.warnings && (
                          <div>
                            <p className="text-xs font-semibold text-gray-500 mb-1">警告信息</p>
                            <pre className="text-xs bg-white rounded border p-2 max-h-20 overflow-auto whitespace-pre-wrap text-yellow-700">
                              {item.warnings}
                            </pre>
                          </div>
                        )}
                        {fields && Object.keys(fields).length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-gray-500 mb-1">提取字段</p>
                            <div className="bg-white rounded border p-2 space-y-1">
                              {Object.entries(fields).map(([k, v]) => (
                                <div key={k} className="flex text-xs">
                                  <span className="text-gray-500 w-20 shrink-0">{k}</span>
                                  <span className="text-gray-800">{String(v)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {!item.ocr_text && !fields && (
                          <p className="text-xs text-gray-400">无详细数据</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* 操作按钮 — 仅 pending 状态显示 */}
                {item.status === 'pending' && (
                  <div className="px-4 pb-3 flex gap-2 bg-gray-50">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleResolve(item.id, 'approved')
                      }}
                      className="px-4 py-1.5 bg-green-600 text-white rounded text-sm font-semibold hover:opacity-90 transition"
                    >
                      通过
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleResolve(item.id, 'rejected')
                      }}
                      className="px-4 py-1.5 bg-red-500 text-white rounded text-sm font-semibold hover:opacity-90 transition"
                    >
                      拒绝
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
