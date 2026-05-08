import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api-client'
import type { StatsData } from '@/types/api'

export function StatsPage() {
  const [data, setData] = useState<StatsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiFetch<StatsData>('/stats/data')
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading || !data) return <div className="text-center py-8 text-muted-foreground">加载中...</div>

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-bold text-[#1d3557]">统计面板</h2>

      {/* 数字汇总 */}
      <div className="grid grid-cols-5 gap-4">
        {[
          { label: '总数', value: data.total, color: 'bg-blue-50 text-blue-700' },
          { label: '通过', value: data.approved, color: 'bg-green-50 text-green-700' },
          { label: '拒绝', value: data.rejected, color: 'bg-red-50 text-red-700' },
          { label: '待复审', value: data.pending_review, color: 'bg-yellow-50 text-yellow-700' },
          { label: '待处理', value: data.pending_queue, color: 'bg-orange-50 text-orange-700' },
        ].map((s) => (
          <div key={s.label} className={`rounded-xl p-4 text-center ${s.color}`}>
            <div className="text-2xl font-bold">{s.value}</div>
            <div className="text-sm mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* 分布 */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white rounded-xl shadow p-4">
          <h3 className="font-semibold text-sm mb-3">文件类型分布</h3>
          {Object.entries(data.type_distribution).map(([type, count]) => (
            <div key={type} className="flex items-center justify-between py-1 text-sm">
              <span>{type}</span>
              <span className="font-mono font-bold">{count}</span>
            </div>
          ))}
        </div>
        <div className="bg-white rounded-xl shadow p-4">
          <h3 className="font-semibold text-sm mb-3">审批结果分布</h3>
          {Object.entries(data.result_distribution).map(([result, count]) => (
            <div key={result} className="flex items-center justify-between py-1 text-sm">
              <span>{result}</span>
              <span className="font-mono font-bold">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
