import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiFetch, apiPost } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import type { LeaveApplication } from '@/types/api'

export function LeaveApplicationDetailPage() {
  const { applicationId } = useParams<{ applicationId: string }>()
  const navigate = useNavigate()
  const [app, setApp] = useState<LeaveApplication | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!applicationId) return
    apiFetch<LeaveApplication>(`/leave-applications/${applicationId}`)
      .then(setApp)
      .catch(() => navigate('/applications'))
      .finally(() => setLoading(false))
  }, [applicationId, navigate])

  const handleApprove = async () => {
    if (!applicationId) return
    await apiPost(`/leave-applications/${applicationId}/approve`, {})
    const updated = await apiFetch<LeaveApplication>(`/leave-applications/${applicationId}`)
    setApp(updated)
  }

  const handleReject = async () => {
    if (!applicationId) return
    await apiPost(`/leave-applications/${applicationId}/reject`, {})
    const updated = await apiFetch<LeaveApplication>(`/leave-applications/${applicationId}`)
    setApp(updated)
  }

  if (loading) return <div className="text-center py-8">加载中...</div>
  if (!app) return null

  const statusStyle: Record<string, string> = {
    SUBMITTED: 'bg-yellow-100 text-yellow-800',
    APPROVED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800',
    STAMPED: 'bg-blue-100 text-blue-800',
    CANCELLED: 'bg-gray-100 text-gray-800',
    EXPIRED: 'bg-gray-100 text-gray-500',
  }

  return (
    <div className="card bg-white rounded-xl shadow p-6 max-w-2xl">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => navigate('/applications')}
          className="text-sm text-[#457b9d] hover:underline"
        >
          ← 返回列表
        </button>
        <h2 className="text-lg font-bold text-[#1d3557]">请假申请详情</h2>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
            {app.application_id}
          </span>
          <span
            className={cn(
              'px-3 py-1 rounded text-sm font-bold',
              statusStyle[app.status] || 'bg-gray-100',
            )}
          >
            {app.status}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">学生姓名：</span>
            {app.student_name}
          </div>
          <div>
            <span className="text-gray-500">学号：</span>
            {app.student_id}
          </div>
          <div>
            <span className="text-gray-500">院系：</span>
            {app.dept || '-'}
          </div>
          <div>
            <span className="text-gray-500">请假类型：</span>
            {app.leave_type}
          </div>
          <div>
            <span className="text-gray-500">开始日期：</span>
            {app.start_date}
          </div>
          <div>
            <span className="text-gray-500">结束日期：</span>
            {app.end_date}
          </div>
        </div>

        <div>
          <span className="text-sm text-gray-500">请假原因：</span>
          <p className="mt-1 p-3 bg-gray-50 rounded text-sm">{app.reason}</p>
        </div>

        {app.qr_content && (app.status === 'APPROVED' || app.status === 'STAMPED') && (
          <div className="border-t pt-4">
            <span className="text-sm text-gray-500 block mb-3">请假条下载（审批通过后可用）：</span>
            <div className="flex items-center gap-6">
              <img
                src={`/api/leave-applications/${app.application_id}/qr/image`}
                alt="请假条二维码"
                className="w-40 h-40 border rounded"
              />
              <div className="flex flex-col gap-2">
                <a
                  href={`/api/leave-applications/${app.application_id}/download`}
                  download
                  className="px-6 py-2 bg-[#457b9d] text-white rounded text-sm font-semibold hover:opacity-90 text-center w-fit"
                >
                  下载请假条 PDF
                </a>
                <p className="text-xs text-gray-400">申请编号：{app.application_id}</p>
                <p className="text-xs text-gray-400">学号：{app.student_id}</p>
                <p className="text-xs text-gray-400">将此 PDF 打印后带至线下盖章</p>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 text-sm text-gray-500 border-t pt-4">
          {app.approved_by && <div>审批人：{app.approved_by}</div>}
          {app.approved_at && <div>审批时间：{app.approved_at}</div>}
          {app.stamped_at && <div>盖章时间：{app.stamped_at}</div>}
          <div>创建时间：{app.created_at}</div>
        </div>

        {app.status === 'SUBMITTED' && (
          <div className="flex gap-3 pt-4 border-t">
            <button
              onClick={handleApprove}
              className="px-6 py-2 bg-green-600 text-white rounded text-sm font-semibold hover:opacity-90"
            >
              审批通过
            </button>
            <button
              onClick={handleReject}
              className="px-6 py-2 bg-red-500 text-white rounded text-sm font-semibold hover:opacity-90"
            >
              拒绝
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
