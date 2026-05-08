import React, { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api-client'
import type { AuditLog } from '@/types/api'

export function LogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)

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
              <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200"></th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => {
              const expanded = expandedId === log.id
              const fields = parseJson(log.fields)
              return (
                <React.Fragment key={log.id}>
                  <tr className="hover:bg-gray-50 cursor-pointer" onClick={() => setExpandedId(expanded ? null : log.id)}>
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
                    <td className="px-3 py-2 border-b border-gray-100 text-xs text-[#457b9d]">
                      {expanded ? '收起' : '详情'}
                    </td>
                  </tr>
                  {expanded && (
                    <tr key={`${log.id}-detail`}>
                      <td colSpan={6} className="px-4 py-4 bg-gray-50 border-b border-gray-200">
                        <div className="grid grid-cols-2 gap-4">
                          {/* 图片预览 */}
                          <div>
                            <p className="text-xs font-semibold text-gray-500 mb-2">文件图像</p>
                            <div className="flex gap-3">
                              {log.before_image && (
                                <div className="flex-1">
                                  <p className="text-xs text-gray-400 mb-1">盖章前</p>
                                  <img
                                    src={`/api/images/${log.before_image}`}
                                    alt="盖章前"
                                    className="w-full max-h-48 object-contain rounded border bg-white"
                                  />
                                </div>
                              )}
                              {log.after_image && (
                                <div className="flex-1">
                                  <p className="text-xs text-gray-400 mb-1">盖章后</p>
                                  <img
                                    src={`/api/images/${log.after_image}`}
                                    alt="盖章后"
                                    className="w-full max-h-48 object-contain rounded border bg-white"
                                  />
                                </div>
                              )}
                              {!log.before_image && !log.after_image && (
                                <p className="text-xs text-gray-400">无图片</p>
                              )}
                            </div>
                          </div>
                          {/* OCR 结果 + 提取字段 */}
                          <div className="space-y-3">
                            {log.ocr_text && (
                              <div>
                                <p className="text-xs font-semibold text-gray-500 mb-1">OCR 识别结果</p>
                                <pre className="text-xs bg-white rounded border p-2 max-h-32 overflow-auto whitespace-pre-wrap">{log.ocr_text}</pre>
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
                            {!log.ocr_text && !fields && (
                              <p className="text-xs text-gray-400">无 OCR 数据</p>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
