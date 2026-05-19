import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { apiFetch, apiPost } from '@/lib/api-client'
import type { CalibrationData, ArmConfig } from '@/types/api'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import { Slider } from '@/components/ui/slider'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogTitle, DialogActions } from '@/components/ui/dialog'

export function CalibrationPage() {
  const { t } = useTranslation('calibration')
  const [cal, setCal] = useState<CalibrationData>({})
  const [config, setConfig] = useState<ArmConfig | null>(null)
  const [servos, setServos] = useState<Record<number, number>>({})
  const [loading, setLoading] = useState(true)
  const [confirmDialog, setConfirmDialog] = useState<{
    title: string
    message: string
    onConfirm: () => void
  } | null>(null)

  useEffect(() => {
    Promise.all([
      apiFetch<CalibrationData>('/calibration/load'),
      apiFetch<ArmConfig>('/calibration/config'),
    ])
      .then(([c, cfg]) => {
        setCal(c)
        setConfig(cfg)
        const mid = cfg.value_mid
        setServos(Object.fromEntries(Array.from({ length: 6 }, (_, i) => [i, mid])))
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const TARGET_POSES = {
    [t('quickPositioning')]: { 0: 1500, 1: 800, 2: 1500, 3: 1700, 4: 1500, 5: 1500 },
  }

  const moveSingle = (servoId: number, pwm: number) => {
    apiPost('/calibration/move_single', { servo_id: servoId, pwm, duration: 100 }).catch(() => {})
  }

  const handleSliderChange = (servoId: number, value: number) => {
    setServos((prev) => ({ ...prev, [servoId]: value }))
    moveSingle(servoId, value)
  }

  const saveCorner = async (corner: string) => {
    await apiPost('/calibration/save_corner', { corner, pwms: servos })
    const newCal = await apiFetch<CalibrationData>('/calibration/load')
    setCal(newCal)
  }

  const goHome = async () => {
    await apiPost('/calibration/home')
    if (config) {
      setServos(Object.fromEntries(Array.from({ length: 6 }, (_, i) => [i, config.value_mid])))
    }
  }

  const goPreset = async (pwms: Record<string, number>) => {
    await apiPost('/calibration/move_multi', { pwms })
  }

  const ping = async () => {
    const res = await apiPost<{ connected: boolean }>('/calibration/ping')
    setConfirmDialog({
      title: t('testConnection'),
      message: res.connected ? t('connectionNormal') : t('connectionFailed'),
      onConfirm: () => setConfirmDialog(null),
    })
  }

  if (loading || !config) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  const corners = cal.corners || {}

  return (
    <div>
      <PageHeader
        title={t('armCalibration')}
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={ping}>
              {t('testConnection')}
            </Button>
            <Button size="sm" onClick={goHome}>
              {t('goHome')}
            </Button>
          </div>
        }
      />

      {/* Servo control */}
      <Card className="mb-6">
        <CardContent className="p-5">
          <h3 className="font-semibold text-foreground mb-5">{t('servoControl')}</h3>
          <div className="space-y-4">
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} className="flex items-center gap-4">
                <span className="w-8 text-sm font-mono font-semibold text-muted-foreground shrink-0">S{i}</span>
                <Slider
                  min={config.value_min}
                  max={config.value_max}
                  value={servos[i] ?? config.value_mid}
                  onChange={(e) => handleSliderChange(i, parseInt(e.target.value))}
                  valueLabel={String(servos[i] ?? config.value_mid)}
                  className="flex-1"
                />
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-border">
            <p className="text-xs text-muted-foreground font-mono">
              Range: {config.value_min} - {config.value_max} · Mid: {config.value_mid}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Quick positioning */}
      <Card className="mb-6">
        <CardContent className="p-5">
          <h3 className="font-semibold text-foreground mb-4">{t('quickPositioning')}</h3>
          <div className="flex flex-wrap gap-3 mb-4">
            {Object.entries(TARGET_POSES).map(([name, pwms]) => (
              <Button
                key={name}
                variant="secondary"
                onClick={() => goPreset(pwms)}
              >
                {name}
              </Button>
            ))}
            <Button
              variant="destructive"
              className="font-bold"
              onClick={() => {
                setConfirmDialog({
                  title: t('testStamp'),
                  message: t('confirmStampAction'),
                  onConfirm: async () => {
                    setConfirmDialog(null)
                    await apiPost('/calibration/test_stamp_sequence')
                  },
                })
              }}
            >
              {t('testStamp')}
            </Button>
          </div>
          <div className="bg-muted/60 rounded-lg px-4 py-3">
            <p className="text-xs text-muted-foreground font-mono">
              {Object.entries(Object.values(TARGET_POSES)[0])
                .map(([s, v]) => `S${s}=${v}`)
                .join('   ')}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Corner calibration */}
      <Card className="mb-6">
        <CardContent className="p-5">
          <h3 className="font-semibold text-foreground mb-4">{t('cornerCalibration')}</h3>
          <div className="grid grid-cols-2 gap-4">
            {['TL', 'TR', 'BL', 'BR'].map((corner) => (
              <Card key={corner}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-mono text-sm font-bold text-foreground">{corner}</span>
                    {corners[corner] ? (
                      <Badge variant="success">{t('calibrated')}</Badge>
                    ) : (
                      <Badge>{t('notCalibrated')}</Badge>
                    )}
                  </div>
                  {corners[corner] && (
                    <div className="mb-3 bg-muted/60 rounded-md px-3 py-2">
                      <p className="text-[11px] font-mono text-muted-foreground leading-relaxed">
                        {Object.entries(corners[corner] as Record<string, number>)
                          .map(([s, v]) => `S${s}=${v}`)
                          .join('  ')}
                      </p>
                    </div>
                  )}
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="success"
                      onClick={() => saveCorner(corner)}
                    >
                      {t('saveCurrentPosition')}
                    </Button>
                    {corners[corner] && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => apiPost('/calibration/test_move', { corner })}
                      >
                        {t('testMove')}
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Reset calibration */}
      <div className="pb-8">
        <Button
          variant="destructive"
          onClick={() => {
            setConfirmDialog({
              title: t('resetCalibration'),
              message: t('confirmReset'),
              onConfirm: async () => {
                setConfirmDialog(null)
                await apiPost('/calibration/reset')
                setCal({})
              },
            })
          }}
        >
          {t('resetCalibration')}
        </Button>
      </div>

      {/* Confirm dialog */}
      <Dialog
        open={confirmDialog !== null}
        onClose={() => setConfirmDialog(null)}
      >
        <DialogTitle>{confirmDialog?.title}</DialogTitle>
        <p className="mt-2 text-sm text-muted-foreground">{confirmDialog?.message}</p>
        <DialogActions>
          <Button variant="secondary" onClick={() => setConfirmDialog(null)}>
            {t('common:cancel')}
          </Button>
          <Button onClick={() => confirmDialog?.onConfirm()}>
            {t('common:confirm')}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  )
}
