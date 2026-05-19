import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { apiFetch, apiPost } from '@/lib/api-client'
import { useAuthStore } from '@/stores/auth-store'
import type { LeaveApplication } from '@/types/api'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { EmptyState } from '@/components/ui/empty-state'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'

const statusBadgeVariant: Record<string, 'warning' | 'success' | 'destructive' | 'info' | 'default'> = {
  SUBMITTED: 'warning',
  APPROVED: 'success',
  REJECTED: 'destructive',
  STAMPED: 'info',
  CANCELLED: 'default',
  EXPIRED: 'default',
}

export function LeaveApplicationsPage() {
  const { t } = useTranslation('applications')
  const [applications, setApplications] = useState<LeaveApplication[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const canApprove = user?.role === 'admin' || user?.role === 'reviewer'

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

  return (
    <div>
      <PageHeader
        title={t('leaveApplications')}
        actions={
          <div className="flex items-center gap-3">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-36"
            >
              <option value="">{t('allStatuses')}</option>
              <option value="SUBMITTED">{t('pendingApproval')}</option>
              <option value="APPROVED">{t('approved')}</option>
              <option value="REJECTED">{t('rejected')}</option>
              <option value="STAMPED">{t('stamped')}</option>
            </Select>
            <Link to="/applications/new">
              <Button size="sm">{t('newApplication')}</Button>
            </Link>
          </div>
        }
      />

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Spinner className="h-6 w-6" />
        </div>
      ) : applications.length === 0 ? (
        <EmptyState title={t('noApplications')} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('applicationId')}</TableHead>
              <TableHead>{t('studentName')}</TableHead>
              <TableHead>{t('studentId')}</TableHead>
              <TableHead>{t('leaveType')}</TableHead>
              <TableHead>{t('startDate')}</TableHead>
              <TableHead>{t('endDate')}</TableHead>
              <TableHead>{t('status')}</TableHead>
              <TableHead>{t('common:actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {applications.map((app) => (
              <TableRow key={app.id}>
                <TableCell className="font-mono text-xs">{app.application_id}</TableCell>
                <TableCell>{app.student_name}</TableCell>
                <TableCell>{app.student_id}</TableCell>
                <TableCell>{app.leave_type}</TableCell>
                <TableCell>{app.start_date}</TableCell>
                <TableCell>{app.end_date}</TableCell>
                <TableCell>
                  <Badge variant={statusBadgeVariant[app.status] || 'default'}>
                    {app.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex gap-1.5">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/applications/${app.application_id}`)}
                    >
                      {t('common:details')}
                    </Button>
                    {app.status === 'SUBMITTED' && canApprove && (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-success"
                          onClick={() => handleApprove(app.application_id)}
                        >
                          {t('approve')}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive"
                          onClick={() => handleReject(app.application_id)}
                        >
                          {t('reject')}
                        </Button>
                      </>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
