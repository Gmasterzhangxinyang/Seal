import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { apiFetch, apiDelete } from '@/lib/api-client'
import type { AuditLog } from '@/types/api'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { EmptyState } from '@/components/ui/empty-state'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogTitle, DialogActions } from '@/components/ui/dialog'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'

const resultBadgeVariant: Record<string, 'success' | 'destructive' | 'warning'> = {
  APPROVED: 'success',
  REJECTED: 'destructive',
  PENDING_REVIEW: 'warning',
}

export function LogsPage() {
  const { t } = useTranslation('logs')
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const fetchLogs = () => {
    apiFetch<AuditLog[]>('/logs')
      .then(setLogs)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchLogs()
  }, [])

  const handleDelete = async () => {
    if (deleteTarget === null) return
    try {
      await apiDelete(`/logs/${deleteTarget}`)
      setLogs((prev) => prev.filter((l) => l.id !== deleteTarget))
      if (expandedId === deleteTarget) setExpandedId(null)
    } catch {
      setDeleteError(t('deleteFailed'))
    } finally {
      setDeleteTarget(null)
    }
  }

  const resultLabel: Record<string, string> = {
    APPROVED: t('approved'),
    REJECTED: t('rejected'),
    PENDING_REVIEW: t('pendingReview'),
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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  return (
    <div>
      <PageHeader title={t('auditLogs')} />

      {logs.length === 0 ? (
        <EmptyState title={t('common:noData')} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('time')}</TableHead>
              <TableHead>{t('operator')}</TableHead>
              <TableHead>{t('docType')}</TableHead>
              <TableHead>{t('result')}</TableHead>
              <TableHead>{t('error')}</TableHead>
              <TableHead className="w-20" />
              <TableHead className="w-20" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {logs.map((log) => {
              const expanded = expandedId === log.id
              const fields = parseJson(log.fields)
              return (
                <React.Fragment key={log.id}>
                  <TableRow
                    className="cursor-pointer"
                    onClick={() => setExpandedId(expanded ? null : log.id)}
                  >
                    <TableCell>{log.timestamp}</TableCell>
                    <TableCell>{log.operator_id}</TableCell>
                    <TableCell>{log.doc_type_name}</TableCell>
                    <TableCell>
                      <Badge variant={resultBadgeVariant[log.result] || 'default'}>
                        {resultLabel[log.result] || log.result}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate">
                      {log.errors || '-'}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm">
                        {expanded ? t('collapse') : t('expand')}
                      </Button>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={(e) => {
                          e.stopPropagation()
                          setDeleteError(null)
                          setDeleteTarget(log.id)
                        }}
                      >
                        {t('delete')}
                      </Button>
                    </TableCell>
                  </TableRow>
                  {expanded && (
                    <TableRow key={`${log.id}-detail`}>
                      <TableCell colSpan={7} className="bg-muted/30 p-4">
                        <Card>
                          <CardContent>
                            <div className="grid grid-cols-2 gap-4">
                              {/* Image preview */}
                              <div>
                                <p className="text-xs font-semibold text-muted-foreground mb-2">
                                  {t('docImage')}
                                </p>
                                <div className="flex gap-3">
                                  {log.before_image && (
                                    <div className="flex-1">
                                      <p className="text-xs text-muted-foreground mb-1">
                                        {t('beforeStamp')}
                                      </p>
                                      <img
                                        src={`/api/images/${log.before_image}`}
                                        alt={t('beforeStamp')}
                                        className="w-full max-h-48 object-contain rounded border border-border bg-card"
                                      />
                                    </div>
                                  )}
                                  {log.after_image && (
                                    <div className="flex-1">
                                      <p className="text-xs text-muted-foreground mb-1">
                                        {t('afterStamp')}
                                      </p>
                                      <img
                                        src={`/api/images/${log.after_image}`}
                                        alt={t('afterStamp')}
                                        className="w-full max-h-48 object-contain rounded border border-border bg-card"
                                      />
                                    </div>
                                  )}
                                  {!log.before_image && !log.after_image && (
                                    <p className="text-xs text-muted-foreground">{t('noImage')}</p>
                                  )}
                                </div>
                              </div>
                              {/* OCR + fields */}
                              <div className="space-y-3">
                                {log.ocr_text && (
                                  <div>
                                    <p className="text-xs font-semibold text-muted-foreground mb-1">
                                      {t('ocrResult')}
                                    </p>
                                    <pre className="text-xs bg-card rounded border border-border p-2 max-h-32 overflow-auto whitespace-pre-wrap">
                                      {log.ocr_text}
                                    </pre>
                                  </div>
                                )}
                                {fields && Object.keys(fields).length > 0 && (
                                  <div>
                                    <p className="text-xs font-semibold text-muted-foreground mb-1">
                                      {t('extractedFields')}
                                    </p>
                                    <div className="bg-card rounded border border-border p-2 space-y-1">
                                      {Object.entries(fields).map(([k, v]) => (
                                        <div key={k} className="flex text-xs">
                                          <span className="text-muted-foreground w-20 shrink-0">
                                            {k}
                                          </span>
                                          <span className="text-foreground">{String(v)}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                {!log.ocr_text && !fields && (
                                  <p className="text-xs text-muted-foreground">{t('noOcrData')}</p>
                                )}
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              )
            })}
          </TableBody>
        </Table>
      )}

      <Dialog open={deleteTarget !== null} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>{t('delete')}</DialogTitle>
        <p className="mt-2 text-sm text-muted-foreground">{t('confirmDelete')}</p>
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
