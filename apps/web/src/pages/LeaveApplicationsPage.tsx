import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiFetch, apiPost } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import type { LeaveApplication } from '@/types/api'

export function LeaveApplicationsPage() {
  const [applications, setApplications] = useState<LeaveApplication[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const navigate = useNavigate()

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const path = statusFilter
        ? `/leave-applications?status=${statusFilter}`
        : '/leave-applications'
      const data = await apiFetch<LeaveApplication[]>(path)
      setApplications(data)
    } catch {
      /* network error */
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh()
  }, [statusFilter, refresh])

  const handleApprove = async (applicationId: string) => {
    await apiPost(`/leave-applications/${applicationId}/approve`, {})
    refresh()
  }

  const handleReject = async (applicationId: string) => {
    await apiPost(`/leave-applications/${applicationId}/reject`, {})
    refresh()
  }

  const statusStyle: Record<string, string> = {
    SUBMITTED: 'bg-yellow-100 text-yellow-800',
    APPROVED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800',
    STAMPED: 'bg-blue-100 text-blue-800',
    CANCELLED: 'bg-gray-100 text-gray-800',
    EXPIRED: 'bg-gray-100 text-gray-500',
  }

  return (
    <div className="card bg-white rounded-xl shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-[#1d3557]">请假申请</h2>
        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 border rounded text-sm"
          >
            <option value="">全部状态</option>
            <option value="SUBMITTED">待审批</option>
            <option value="APPROVED">已审批</option>
            <option value="REJECTED">已拒绝</option>
            <option value="STAMPED">已盖章</option>
          </select>
          <Link
            to="/applications/new"
            className="px-4 py-1.5 bg-[#457b9d] text-white rounded text-sm font-semibold hover:opacity-90"
          >
            新建申请
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-8 text-muted-foreground">加载中...</div>
      ) : applications.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">暂无申请记录</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr>
                <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">
                  申请编号
                </th>
                <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">
                  学生姓名
                </th>
                <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">学号</th>
                <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">
                  请假类型
                </th>
                <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">
                  开始日期
                </th>
                <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">
                  结束日期
                </th>
                <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">状态</th>
                <th className="bg-gray-50 px-3 py-2 text-left border-b-2 border-gray-200">操作</th>
              </tr>
            </thead>
            <tbody>
              {applications.map((app) => (
                <tr key={app.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 border-b border-gray-100 font-mono text-xs">
                    {app.application_id}
                  </td>
                  <td className="px-3 py-2 border-b border-gray-100">{app.student_name}</td>
                  <td className="px-3 py-2 border-b border-gray-100">{app.student_id}</td>
                  <td className="px-3 py-2 border-b border-gray-100">{app.leave_type}</td>
                  <td className="px-3 py-2 border-b border-gray-100">{app.start_date}</td>
                  <td className="px-3 py-2 border-b border-gray-100">{app.end_date}</td>
                  <td className="px-3 py-2 border-b border-gray-100">
                    <span
                      className={cn(
                        'inline-block px-2 py-0.5 rounded text-xs font-bold',
                        statusStyle[app.status] || 'bg-gray-100',
                      )}
                    >
                      {app.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 border-b border-gray-100">
                    <div className="flex gap-1.5">
                      <button
                        onClick={() => navigate(`/applications/${app.application_id}`)}
                        className="px-2 py-1 text-xs text-[#457b9d] hover:underline"
                      >
                        详情
                      </button>
                      {app.status === 'SUBMITTED' && (
                        <>
                          <button
                            onClick={() => handleApprove(app.application_id)}
                            className="px-2 py-1 text-xs text-green-600 hover:underline"
                          >
                            审批
                          </button>
                          <button
                            onClick={() => handleReject(app.application_id)}
                            className="px-2 py-1 text-xs text-red-500 hover:underline"
                          >
                            拒绝
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
