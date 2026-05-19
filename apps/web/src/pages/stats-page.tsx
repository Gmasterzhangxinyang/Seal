import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { apiFetch } from '@/lib/api-client'
import type { StatsData } from '@/types/api'
import { PageHeader } from '@/components/layout/page-header'
import { Spinner } from '@/components/ui/spinner'
import { Card, CardContent } from '@/components/ui/card'
import { TrendingUp, TrendingDown, Minus, Clock, BarChart3 } from 'lucide-react'

const iconMap = {
  total: BarChart3,
  approved: TrendingUp,
  rejected: TrendingDown,
  pendingReview: Clock,
  pendingQueue: Minus,
}

export function StatsPage() {
  const { t } = useTranslation('admin')
  const [data, setData] = useState<StatsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiFetch<StatsData>('/stats/data')
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  const summaryCards = [
    { key: 'total', label: t('total'), value: data.total },
    { key: 'approved', label: t('approved'), value: data.approved },
    { key: 'rejected', label: t('rejected'), value: data.rejected },
    { key: 'pendingReview', label: t('pendingReview'), value: data.pending_review },
    { key: 'pendingQueue', label: t('pendingQueue'), value: data.pending_queue },
  ]

  const total = data.total || 1
  const typeEntries = Object.entries(data.type_distribution).sort((a, b) => (b[1] as number) - (a[1] as number))
  const resultEntries = Object.entries(data.result_distribution).sort((a, b) => (b[1] as number) - (a[1] as number))

  const resultColorMap: Record<string, string> = {
    APPROVED: 'bg-success',
    REJECTED: 'bg-destructive',
    PENDING_REVIEW: 'bg-warning',
  }

  return (
    <div>
      <PageHeader title={t('statisticsPanel')} />

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {summaryCards.map((s) => {
          const Icon = iconMap[s.key as keyof typeof iconMap] || BarChart3
          const pct = Math.round(((s.value as number) / total) * 100)
          return (
            <Card key={s.label} hover>
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="p-2 rounded-lg bg-muted">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <span className="text-xs font-mono tabular-nums text-muted-foreground">{pct}%</span>
                </div>
                <div className="text-3xl font-bold tabular-nums text-foreground leading-none mb-1">
                  {s.value}
                </div>
                <span className="text-sm text-muted-foreground">{s.label}</span>
                <div className="mt-3 h-1 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary/60 transition-all duration-300 ease-out"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Distribution panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
        {/* Doc type distribution */}
        <Card>
          <CardContent className="p-5">
            <h3 className="font-semibold text-sm text-foreground mb-4">
              {t('docTypeDistribution')}
            </h3>
            <div className="space-y-3">
              {typeEntries.map(([type, count]) => {
                const pct = Math.round(((count as number) / total) * 100)
                return (
                  <div key={type} className="space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-foreground font-medium truncate mr-3">{type}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="font-mono tabular-nums text-muted-foreground">{count}</span>
                        <span className="text-xs text-muted-foreground/60 w-10 text-right">{pct}%</span>
                      </div>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary/50 transition-all duration-300 ease-out"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
              {typeEntries.length === 0 && (
                <p className="text-sm text-muted-foreground py-2">No data</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Result distribution */}
        <Card>
          <CardContent className="p-5">
            <h3 className="font-semibold text-sm text-foreground mb-4">
              {t('resultDistribution')}
            </h3>
            <div className="space-y-3">
              {resultEntries.map(([result, count]) => {
                const pct = Math.round(((count as number) / total) * 100)
                const barColor = resultColorMap[result] || 'bg-primary/50'
                return (
                  <div key={result} className="space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className={`inline-block w-2 h-2 rounded-full ${barColor}`} />
                        <span className="text-foreground font-medium">{result}</span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="font-mono tabular-nums text-muted-foreground">{count}</span>
                        <span className="text-xs text-muted-foreground/60 w-10 text-right">{pct}%</span>
                      </div>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className={`h-full rounded-full ${barColor} transition-all duration-300 ease-out`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
              {resultEntries.length === 0 && (
                <p className="text-sm text-muted-foreground py-2">No data</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
