import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { apiPost } from '@/lib/api-client'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'

export function NewLeaveApplicationPage() {
  const { t } = useTranslation('applications')
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
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
    setError(null)
    try {
      const result = await apiPost<{ application_id: string }>('/leave-applications', form)
      navigate(`/applications/${result.application_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('common:unknownError'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader title={t('newLeaveApplication')} />

      <Card className="max-w-xl mx-auto pt-6">
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  {t('studentId')} *
                </label>
                <Input
                  name="student_id"
                  value={form.student_id}
                  onChange={handleChange}
                  required
                  placeholder="20230001"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  {t('studentName')} *
                </label>
                <Input
                  name="student_name"
                  value={form.student_name}
                  onChange={handleChange}
                  required
                  placeholder="..."
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                {t('department')}
              </label>
              <Input
                name="dept"
                value={form.dept}
                onChange={handleChange}
                placeholder="..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                {t('leaveType')} *
              </label>
              <Select
                name="leave_type"
                value={form.leave_type}
                onChange={handleChange}
                required
              >
                <option value="病假">{t('sickLeave')}</option>
                <option value="事假">{t('personalLeave')}</option>
                <option value="婚假">{t('marriageLeave')}</option>
                <option value="产假">{t('maternityLeave')}</option>
                <option value="丧假">{t('bereavementLeave')}</option>
                <option value="公假">{t('officialLeave')}</option>
                <option value="其他">{t('other')}</option>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  {t('startDate')} *
                </label>
                <Input
                  name="start_date"
                  type="date"
                  value={form.start_date}
                  onChange={handleChange}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  {t('endDate')} *
                </label>
                <Input
                  name="end_date"
                  type="date"
                  value={form.end_date}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                {t('leaveReason')} *
              </label>
              <Textarea
                name="reason"
                value={form.reason}
                onChange={handleChange}
                required
                rows={3}
                className="min-h-[80px]"
                placeholder="..."
              />
            </div>

            {error && (
              <p className="text-sm text-destructive">{t('createFailed')}: {error}</p>
            )}

            <div className="flex gap-3 pt-2">
              <Button type="submit" loading={loading}>
                {loading ? t('submitting') : t('submitApplication')}
              </Button>
              <Button type="button" variant="secondary" onClick={() => navigate('/applications')}>
                {t('common:cancel')}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
