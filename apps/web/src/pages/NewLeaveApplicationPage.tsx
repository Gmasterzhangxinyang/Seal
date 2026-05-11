import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiPost } from '@/lib/api-client'

export function NewLeaveApplicationPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    student_id: '',
    student_name: '',
    dept: '',
    leave_type: '病假',
    start_date: '',
    end_date: '',
    reason: '',
  })

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const result = await apiPost<{ application_id: string }>('/leave-applications', form)
      navigate(`/applications/${result.application_id}`)
    } catch (err) {
      alert('创建失败: ' + (err instanceof Error ? err.message : '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card bg-white rounded-xl shadow p-6 max-w-xl mx-auto">
      <h2 className="text-lg font-bold text-[#1d3557] mb-6">新建请假申请</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">学号 *</label>
            <input
              name="student_id"
              value={form.student_id}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border rounded text-sm"
              placeholder="20230001"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">姓名 *</label>
            <input
              name="student_name"
              value={form.student_name}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border rounded text-sm"
              placeholder="张三"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">院系</label>
          <input
            name="dept"
            value={form.dept}
            onChange={handleChange}
            className="w-full px-3 py-2 border rounded text-sm"
            placeholder="智能工程学院"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">请假类型 *</label>
          <select
            name="leave_type"
            value={form.leave_type}
            onChange={handleChange}
            required
            className="w-full px-3 py-2 border rounded text-sm"
          >
            <option value="病假">病假</option>
            <option value="事假">事假</option>
            <option value="婚假">婚假</option>
            <option value="产假">产假</option>
            <option value="丧假">丧假</option>
            <option value="公假">公假</option>
            <option value="其他">其他</option>
          </select>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">开始日期 *</label>
            <input
              name="start_date"
              type="date"
              value={form.start_date}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border rounded text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">结束日期 *</label>
            <input
              name="end_date"
              type="date"
              value={form.end_date}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border rounded text-sm"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">请假原因 *</label>
          <textarea
            name="reason"
            value={form.reason}
            onChange={handleChange}
            required
            rows={3}
            className="w-full px-3 py-2 border rounded text-sm"
            placeholder="请输入请假原因..."
          />
        </div>
        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-[#457b9d] text-white rounded text-sm font-semibold hover:opacity-90 disabled:opacity-50"
          >
            {loading ? '提交中...' : '提交申请'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/applications')}
            className="px-6 py-2 bg-gray-100 text-gray-700 rounded text-sm font-semibold hover:bg-gray-200"
          >
            取消
          </button>
        </div>
      </form>
    </div>
  )
}
