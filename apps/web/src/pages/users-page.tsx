import { useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { apiFetch, apiDelete } from '@/lib/api-client'
import { useAuthStore } from '@/stores/auth-store'
import type { UserItem } from '@/types/api'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { EmptyState } from '@/components/ui/empty-state'
import { Dialog, DialogTitle, DialogActions } from '@/components/ui/dialog'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'

const roleBadgeVariant: Record<string, 'default' | 'info'> = {
  admin: 'info',
  reviewer: 'default',
  operator: 'default',
}

export function UsersPage() {
  const { t } = useTranslation('admin')
  const currentUser = useAuthStore((s) => s.user)
  const [users, setUsers] = useState<UserItem[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<UserItem[]>('/users')
      setUsers(data)
    } catch {
      /* ignore */
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load()
  }, [load])

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await apiDelete(`/users/${deleteTarget}`)
      setUsers((prev) => prev.filter((u) => u.username !== deleteTarget))
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : t('deleteFailed'))
    } finally {
      setDeleteTarget(null)
    }
  }

  const roleLabel: Record<string, string> = {
    admin: t('roleAdmin'),
    reviewer: t('roleReviewer'),
    operator: t('roleOperator'),
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  return (
    <div>
      <PageHeader title={t('userManagement')} />

      {users.length === 0 ? (
        <EmptyState title={t('noUsers')} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('username')}</TableHead>
              <TableHead>{t('email')}</TableHead>
              <TableHead>{t('role')}</TableHead>
              <TableHead>{t('registrationTime')}</TableHead>
              <TableHead className="text-right">{t('common:actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((u) => {
              const isSelf = u.username === currentUser?.username
              return (
                <TableRow key={u.username}>
                  <TableCell className="font-medium">
                    {u.username}
                    {isSelf && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {t('current')}
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{u.email || '-'}</TableCell>
                  <TableCell>
                    <Badge variant={roleBadgeVariant[u.role] || 'default'}>
                      {roleLabel[u.role] || u.role}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{u.created_at || '-'}</TableCell>
                  <TableCell className="text-right">
                    {isSelf ? (
                      <span className="text-xs text-muted-foreground">-</span>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => {
                          setDeleteError(null)
                          setDeleteTarget(u.username)
                        }}
                      >
                        {t('delete')}
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      )}

      <Dialog open={deleteTarget !== null} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>{t('delete')}</DialogTitle>
        <p className="mt-2 text-sm text-muted-foreground">
          {t('confirmDeleteUser', { username: deleteTarget || '' })}
        </p>
        {deleteError && (
          <p className="mt-2 text-sm text-destructive">{deleteError}</p>
        )}
        <DialogActions>
          <Button variant="secondary" onClick={() => setDeleteTarget(null)}>
            {t('common:cancel')}
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            {t('common:confirm')}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  )
}
