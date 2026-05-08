import { useEffect, useState } from 'react'
import { apiFetch, apiPost } from '@/lib/api-client'
import type { ReviewItem } from '@/types/api'

export function ReviewPage() {
  const [pending, setPending] = useState<ReviewItem[]>([])
  const [allItems, setAllItems] = useState<ReviewItem[]>([])
  const [tab, setTab] = useState<'pending' | 'all'>('pending')
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    setLoading(true)
    try {
      const [p, a] = await Promise.all([
        apiFetch<ReviewItem[]>('/review/pending'),
        apiFetch<ReviewItem[]>('/review/all'),
      ])
      setPending(p)
      setAllItems(a)
    } catch {} finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, [])

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
          {items.map((item) => (
            <div key={item.id} className="border rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-semibold">#{item.id}</span>
                  <span className="mx-2 text-gray-400">·</span>
                  <span>{item.doc_type_name}</span>
                  <span className="mx-2 text-gray-400">·</span>
                  <span className="text-sm text-gray-500">{item.operator_id}</span>
                  <span className="mx-2 text-gray-400">·</span>
                  <span className="text-sm text-gray-500">{item.timestamp}</span>
                </div>
                <span className="text-xs font-bold px-2 py-0.5 rounded bg-gray-100">
                  {statusLabel[item.status] || item.status}
                </span>
              </div>
              {item.status === 'pending' && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => handleResolve(item.id, 'approved')}
                    className="px-3 py-1 bg-green-600 text-white rounded text-sm font-semibold hover:opacity-90"
                  >
                    通过
                  </button>
                  <button
                    onClick={() => handleResolve(item.id, 'rejected')}
                    className="px-3 py-1 bg-red-500 text-white rounded text-sm font-semibold hover:opacity-90"
                  >
                    拒绝
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
