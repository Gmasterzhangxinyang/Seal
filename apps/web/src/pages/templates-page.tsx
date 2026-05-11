import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch, apiDelete } from '@/lib/api-client'
import type { Template } from '@/types/api'

export function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    try {
      const data = await apiFetch<Template[]>('/templates')
      setTemplates(data)
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

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除此模板？')) return
    try {
      await apiDelete(`/templates/${id}`)
      refresh()
    } catch (err) {
      alert(err instanceof Error ? err.message : '删除失败')
    }
  }

  const handleExport = async (id: number) => {
    window.open(`/api/templates/${id}/export`, '_blank')
  }

  if (loading) return <div className="text-center py-8 text-muted-foreground">加载中...</div>

  return (
    <div className="card bg-white rounded-xl shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-[#1d3557]">模板管理</h2>
        <div className="flex gap-2">
          <button
            onClick={() => window.open('/api/templates/export/all', '_blank')}
            className="px-3 py-1.5 bg-gray-100 text-sm rounded-lg hover:bg-gray-200"
          >
            导出全部
          </button>
          <Link
            to="/admin/templates/new"
            className="px-3 py-1.5 bg-[#457b9d] text-white text-sm rounded-lg hover:opacity-90"
          >
            新建模板
          </Link>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">名称</th>
              <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">编码</th>
              <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">字段数</th>
              <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">操作</th>
            </tr>
          </thead>
          <tbody>
            {templates.map((tpl) => (
              <tr key={tpl.id} className="hover:bg-gray-50">
                <td className="px-3 py-2 border-b border-gray-100 font-medium">{tpl.name}</td>
                <td className="px-3 py-2 border-b border-gray-100">
                  <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">{tpl.code}</code>
                </td>
                <td className="px-3 py-2 border-b border-gray-100">
                  {tpl.field_stats
                    ? `${tpl.field_stats.required}必填 / ${tpl.field_stats.optional}选填`
                    : tpl.fields?.length || 0}
                </td>
                <td className="px-3 py-2 border-b border-gray-100">
                  <div className="flex gap-2">
                    <Link
                      to={`/admin/templates/${tpl.id}/edit`}
                      className="text-[#457b9d] hover:underline text-xs"
                    >
                      编辑
                    </Link>
                    <button
                      onClick={() => handleExport(tpl.id)}
                      className="text-gray-500 hover:underline text-xs"
                    >
                      导出
                    </button>
                    {!tpl.is_system && (
                      <button
                        onClick={() => handleDelete(tpl.id)}
                        className="text-red-500 hover:underline text-xs"
                      >
                        删除
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
