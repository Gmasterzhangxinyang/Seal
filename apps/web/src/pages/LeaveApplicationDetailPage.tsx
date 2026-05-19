import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { apiFetch, apiPost } from '@/lib/api-client'
import { useAuthStore } from '@/stores/auth-store'
import type { LeaveApplication } from '@/types/api'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { Card, CardContent } from '@/components/ui/card'

const statusBadgeVariant: Record<string, 'warning' | 'success' | 'destructive' | 'info' | 'default'> = {
  SUBMITTED: 'warning',
  APPROVED: 'success',
  REJECTED: 'destructive',
  STAMPED: 'info',
  CANCELLED: 'default',
  EXPIRED: 'default',
}

export function LeaveApplicationDetailPage() {
  const { t } = useTranslation('applications')
  const { applicationId } = useParams<{ applicationId: string }>()
  const navigate = useNavigate()
  const [app, setApp] = useState<LeaveApplication | null>(null)
  const [loading, setLoading] = useState(true)
  const user = useAuthStore((s) => s.user)
  const canApprove = user?.role === 'admin' || user?.role === 'reviewer'

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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }
  if (!app) return null

  return (
    <div>
      <PageHeader
        title={t('leaveApplicationDetail')}
        actions={
          <Button variant="ghost" size="sm" onClick={() => navigate('/applications')}>
            &larr; {t('backToList')}
          </Button>
        }
      />

      <Card className="max-w-2xl pt-6">
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm bg-muted px-2 py-1 rounded">
                {app.application_id}
              </span>
              <Badge variant={statusBadgeVariant[app.status] || 'default'}>
                {app.status}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">{t('studentName')}：</span>
                {app.student_name}
              </div>
              <div>
                <span className="text-muted-foreground">{t('studentId')}：</span>
                {app.student_id}
              </div>
              <div>
                <span className="text-muted-foreground">{t('department')}：</span>
                {app.dept || '-'}
              </div>
              <div>
                <span className="text-muted-foreground">{t('leaveType')}：</span>
                {app.leave_type}
              </div>
              <div>
                <span className="text-muted-foreground">{t('startDate')}：</span>
                {app.start_date}
              </div>
              <div>
                <span className="text-muted-foreground">{t('endDate')}：</span>
                {app.end_date}
              </div>
            </div>

            <div>
              <span className="text-sm text-muted-foreground">{t('leaveReason')}：</span>
              <p className="mt-1 p-3 bg-muted rounded text-sm">{app.reason}</p>
            </div>

            {app.qr_content && (app.status === 'APPROVED' || app.status === 'STAMPED') && (
              <div className="border-t border-border pt-4">
                <span className="text-sm text-muted-foreground block mb-3">
                  {t('leaveNoteDownload')}
                </span>
                <div className="flex items-center gap-6">
                  <img
                    src={`/api/leave-applications/${app.application_id}/qr/image`}
                    alt={t('leaveNoteQrCode')}
                    className="w-40 h-40 border border-border rounded bg-card"
                  />
                  <div className="flex flex-col gap-2">
                    <a
                      href={`/api/leave-applications/${app.application_id}/download`}
                      download
                    >
                      <Button>{t('downloadPdf')}</Button>
                    </a>
                    <p className="text-xs text-muted-foreground">
                      {t('applicationId')}: {app.application_id}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {t('studentId')}: {app.student_id}
                    </p>
                    <p className="text-xs text-muted-foreground">{t('printAndStamp')}</p>
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4 text-sm text-muted-foreground border-t border-border pt-4">
              {app.approved_by && <div>{t('approver')}: {app.approved_by}</div>}
              {app.approved_at && <div>{t('approvalTime')}: {app.approved_at}</div>}
              {app.stamped_at && <div>{t('stampTime')}: {app.stamped_at}</div>}
              <div>{t('createdTime')}: {app.created_at}</div>
            </div>

            {app.ai_comment && (
              <div className="border-t border-border pt-4">
                <span className="text-sm text-muted-foreground">{t('aiApprovalComment')}：</span>
                <p className="mt-1 p-3 bg-muted rounded text-sm">{app.ai_comment}</p>
              </div>
            )}

            {app.status === 'SUBMITTED' && canApprove && (
              <div className="flex gap-3 pt-4 border-t border-border">
                <Button variant="success" onClick={handleApprove}>
                  {t('approveBtn')}
                </Button>
                <Button variant="destructive" onClick={handleReject}>
                  {t('reject')}
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
