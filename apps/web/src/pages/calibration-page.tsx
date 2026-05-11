import { useEffect, useState } from 'react'
import { apiFetch, apiPost } from '@/lib/api-client'
import type { CalibrationData, ArmConfig } from '@/types/api'

export function CalibrationPage() {
  const [cal, setCal] = useState<CalibrationData>({})
  const [config, setConfig] = useState<ArmConfig | null>(null)
  const [servos, setServos] = useState<Record<number, number>>({})
  const [loading, setLoading] = useState(true)

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
    快速定位: { 0: 1500, 1: 800, 2: 1500, 3: 1700, 4: 1500, 5: 1500 },
  }

  const moveSingle = (servoId: number, pwm: number) => {
    apiPost('/calibration/move_single', { servo_id: servoId, pwm, duration: 20 })
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
    alert(res.connected ? '连接正常' : '连接失败')
  }

  if (loading || !config) return <div className="text-center py-8 text-muted-foreground">加载中...</div>

  const corners = cal.corners || {}

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-[#1d3557]">机械臂标定</h2>
        <div className="flex gap-2">
          <button onClick={ping} className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm hover:bg-gray-200">
            测试连接
          </button>
          <button onClick={goHome} className="px-3 py-1.5 bg-[#457b9d] text-white rounded-lg text-sm hover:opacity-90">
            回中位
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow p-6">
        <h3 className="font-semibold mb-4">舵机控制</h3>
        <div className="space-y-4">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="flex items-center gap-4">
              <span className="w-16 text-sm font-mono">S{i}</span>
              <input
                type="range"
                min={config.value_min}
                max={config.value_max}
                value={servos[i] ?? config.value_mid}
                onChange={(e) => handleSliderChange(i, parseInt(e.target.value))}
                className="flex-1"
              />
              <span className="w-16 text-sm font-mono text-right">{servos[i] ?? config.value_mid}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow p-6">
        <h3 className="font-semibold mb-4">快速定位</h3>
        <div className="flex flex-wrap gap-2">
          {Object.entries(TARGET_POSES).map(([name, pwms]) => (
            <button
              key={name}
              onClick={() => goPreset(pwms)}
              className="px-4 py-2 bg-[#1d3557] text-white rounded-lg text-sm hover:opacity-90"
            >
              {name}
            </button>
          ))}
          <button
            onClick={async () => {
              if (confirm('确定执行盖章动作？')) {
                await apiPost('/calibration/test_stamp_sequence')
              }
            }}
            className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:opacity-90 font-bold"
          >
            测试盖章
          </button>
        </div>
        <div className="mt-3 text-xs text-gray-500 font-mono">
          {Object.entries(TARGET_POSES.快速定位).map(([s, v]) => `S${s}=${v}`).join('  ')}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow p-6">
        <h3 className="font-semibold mb-4">四角标定</h3>
        <div className="grid grid-cols-2 gap-4">
          {['TL', 'TR', 'BL', 'BR'].map((corner) => (
            <div key={corner} className="border rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-sm font-bold">{corner}</span>
                {corners[corner] ? (
                  <span className="text-xs text-green-600">已标定</span>
                ) : (
                  <span className="text-xs text-gray-400">未标定</span>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => saveCorner(corner)}
                  className="px-2 py-1 bg-green-600 text-white rounded text-xs hover:opacity-90"
                >
                  保存当前位置
                </button>
                {corners[corner] && (
                  <button
                    onClick={() => apiPost('/calibration/test_move', { corner })}
                    className="px-2 py-1 bg-gray-100 rounded text-xs hover:bg-gray-200"
                  >
                    测试移动
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <button
        onClick={async () => {
          if (confirm('确定重置所有标定数据？')) {
            await apiPost('/calibration/reset')
            setCal({})
          }
        }}
        className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm hover:opacity-90"
      >
        重置标定
      </button>
    </div>
  )
}
