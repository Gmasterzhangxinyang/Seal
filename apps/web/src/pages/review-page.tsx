import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { apiFetch, apiPost } from '@/lib/api-client'
import type { ReviewItem } from '@/types/api'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { EmptyState } from '@/components/ui/empty-state'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'

const statusBadgeVariant: Record<string, 'warning' | 'success' | 'destructive' | 'info'> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'destructive',
  stamping: 'info',
}

export function ReviewPage() {
  const { t } = useTranslation('review')
  const [pending, setPending] = useState<ReviewItem[]>([])
  const [allItems, setAllItems] = useState<ReviewItem[]>([])
  const [tab, setTab] = useState<string>('pending')
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const refresh = async () => {
    setLoading(true)
    try {
      const [p, a] = await Promise.all([
        apiFetch<ReviewItem[]>('/review/pending'),
        apiFetch<ReviewItem[]>('/review/all'),
      ])
      setPending(p)
      setAllItems(a)
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

  const handleResolve = async (id: number, decision: string) => {
    await apiPost(`/review/${id}/resolve`, { decision })
    refresh()
  }

  const items = tab === 'pending' ? pending : allItems

  const statusLabel: Record<string, string> = {
    pending: t('statusPending'),
    approved: t('statusApproved'),
    rejected: t('statusRejected'),
    stamping: t('statusStamping'),
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

  const renderItem = (item: ReviewItem) => {
    const expanded = expandedId === item.id
    const fields = parseJson(item.doc_fields)
    return (
      <Card key={item.id} hover>
        <div
          className="flex items-center justify-between p-4 cursor-pointer"
          onClick={() => setExpandedId(expanded ? null : item.id)}
        >
          <div className="flex items-center gap-2 text-sm">
            <span className="font-semibold">#{item.id}</span>
            <span className="text-muted-foreground">-</span>
            <span>{item.doc_type_name}</span>
            <span className="text-muted-foreground">-</span>
            <span className="text-muted-foreground">{item.operator_id}</span>
            <span className="text-muted-foreground">-</span>
            <span className="text-muted-foreground">{item.timestamp}</span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={statusBadgeVariant[item.status] || 'default'}>
              {statusLabel[item.status] || item.status}
            </Badge>
            <span className="text-xs text-primary">
              {expanded ? t('collapse') : t('expand')}
            </span>
          </div>
        </div>

        {expanded && (
          <div className="px-4 pb-4 bg-muted/30 border-t border-border">
            <div className="grid grid-cols-2 gap-4 mt-3">
              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-2">
                  {t('docImage')}
                </p>
                {item.image_path ? (
                  <img
                    src={`/api/images/${item.image_path}`}
                    alt={t('reviewFile')}
                    className="w-full max-h-48 object-contain rounded border border-border bg-card"
                  />
                ) : (
                  <p className="text-xs text-muted-foreground">{t('noImage')}</p>
                )}
              </div>
              <div className="space-y-3">
                {item.ocr_text && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground mb-1">
                      {t('ocrResult')}
                    </p>
                    <pre className="text-xs bg-card rounded border border-border p-2 max-h-32 overflow-auto whitespace-pre-wrap">
                      {item.ocr_text}
                    </pre>
                  </div>
                )}
                {item.warnings && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground mb-1">
                      {t('warnings')}
                    </p>
                    <pre className="text-xs bg-card rounded border border-border p-2 max-h-20 overflow-auto whitespace-pre-wrap text-warning">
                      {item.warnings}
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
                          <span className="text-muted-foreground w-20 shrink-0">{k}</span>
                          <span className="text-foreground">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {!item.ocr_text && !fields && (
                  <p className="text-xs text-muted-foreground">{t('noDetailData')}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {item.status === 'pending' && (
          <div className="px-4 pb-3 flex gap-2 bg-muted/30">
            <Button
              size="sm"
              variant="success"
              onClick={(e) => {
                e.stopPropagation()
                handleResolve(item.id, 'approved')
              }}
            >
              {t('approve')}
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={(e) => {
                e.stopPropagation()
                handleResolve(item.id, 'rejected')
              }}
            >
              {t('reject')}
            </Button>
          </div>
        )}
      </Card>
    )
  }

  return (
    <div>
      <PageHeader title={t('manualReview')} />

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Spinner className="h-6 w-6" />
        </div>
      ) : (
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="pending" count={pending.length}>
              {t('pending')}
            </TabsTrigger>
            <TabsTrigger value="all" count={allItems.length}>
              {t('all')}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="pending">
            {pending.length === 0 ? (
              <EmptyState title={t('noData')} />
            ) : (
              <div className="space-y-3">{pending.map(renderItem)}</div>
            )}
          </TabsContent>

          <TabsContent value="all">
            {allItems.length === 0 ? (
              <EmptyState title={t('noData')} />
            ) : (
              <div className="space-y-3">{allItems.map(renderItem)}</div>
            )}
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
