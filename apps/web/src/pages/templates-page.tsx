import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { apiFetch, apiDelete } from '@/lib/api-client'
import type { Template } from '@/types/api'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
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

export function TemplatesPage() {
  const { t } = useTranslation('admin')
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

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

  const handleDelete = async () => {
    if (deleteTarget === null) return
    try {
      await apiDelete(`/templates/${deleteTarget}`)
      refresh()
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : t('deleteFailed'))
    } finally {
      setDeleteTarget(null)
    }
  }

  const handleExport = async (id: number) => {
    window.open(`/api/templates/${id}/export`, '_blank')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title={t('templateManagement')}
        actions={
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => window.open('/api/templates/export/all', '_blank')}
            >
              {t('exportAll')}
            </Button>
            <Link to="/admin/templates/new">
              <Button size="sm">{t('newTemplate')}</Button>
            </Link>
          </div>
        }
      />

      {templates.length === 0 ? (
        <EmptyState title={t('common:noData')} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('templateName')}</TableHead>
              <TableHead>{t('templateCode')}</TableHead>
              <TableHead>{t('fieldCount')}</TableHead>
              <TableHead>{t('common:actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {templates.map((tpl) => (
              <TableRow key={tpl.id}>
                <TableCell className="font-medium">{tpl.name}</TableCell>
                <TableCell>
                  <code className="bg-muted px-1.5 py-0.5 rounded text-xs">{tpl.code}</code>
                </TableCell>
                <TableCell>
                  {tpl.field_stats
                    ? `${tpl.field_stats.required} / ${tpl.field_stats.optional}`
                    : tpl.fields?.length || 0}
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Link to={`/admin/templates/${tpl.id}/edit`}>
                      <Button variant="ghost" size="sm">
                        {t('edit')}
                      </Button>
                    </Link>
                    <Button variant="ghost" size="sm" onClick={() => handleExport(tpl.id)}>
                      {t('export')}
                    </Button>
                    {!tpl.is_system && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => {
                          setDeleteError(null)
                          setDeleteTarget(tpl.id)
                        }}
                      >
                        {t('delete')}
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Dialog open={deleteTarget !== null} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>{t('delete')}</DialogTitle>
        <p className="mt-2 text-sm text-muted-foreground">{t('confirmDeleteTemplate')}</p>
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
