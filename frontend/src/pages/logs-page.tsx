import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api-client'
import type { AuditLog } from '@/types/api'

export function LogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiFetch<AuditLog[]>('/logs')
      .then(setLogs)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="text-center py-8 text-muted-foreground">加载中...</div>
  }

  const resultLabel: Record<string, string> = {
    APPROVED: '通过',
    REJECTED: '拒绝',
    PENDING_REVIEW: '待复审',
  }
  const resultStyle: Record<string, string> = {
    APPROVED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800',
    PENDING_REVIEW: 'bg-yellow-100 text-yellow-800',
  }

  return (
    <div className="card bg-white rounded-xl shadow p-6">
      <h2 className="text-lg font-bold text-[#1d3557] mb-4">审计日志</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr>
              <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">时间</th>
              <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">操作员</th>
              <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">文件类型</th>
              <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">结果</th>
              <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">错误</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="px-3 py-2 border-b border-gray-100">{log.timestamp}</td>
                <td className="px-3 py-2 border-b border-gray-100">{log.operator_id}</td>
                <td className="px-3 py-2 border-b border-gray-100">{log.doc_type_name}</td>
                <td className="px-3 py-2 border-b border-gray-100">
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${resultStyle[log.result] || 'bg-gray-100'}`}>
                    {resultLabel[log.result] || log.result}
                  </span>
                </td>
                <td className="px-3 py-2 border-b border-gray-100 text-xs text-gray-500 max-w-[200px] truncate">
                  {log.errors || '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
