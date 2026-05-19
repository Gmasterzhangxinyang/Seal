import { useState, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

let _currentAudio: HTMLAudioElement | null = null
let _audioUnlocked = false

function unlockAudio() {
  if (_audioUnlocked) return
  try {
    // 创建一个空的 AudioContext 并在用户手势中 resume，
    // 浏览器会标记此页面为"用户已交互"，后续异步 audio.play() 才不会被拦截
    const ctx = new AudioContext()
    if (ctx.state === 'suspended') {
      ctx.resume().then(() => { _audioUnlocked = true; ctx.close() }).catch(() => ctx.close())
    } else {
      _audioUnlocked = true
      ctx.close()
    }
  } catch {
    // AudioContext not supported (extremely rare), just flag as unlocked
    _audioUnlocked = true
  }
}

function playAudioBlob(blob: Blob, label = 'audio') {
  _currentAudio?.pause()
  _currentAudio = null
  const url = URL.createObjectURL(blob)
  const audio = new Audio(url)
  _currentAudio = audio
  audio.onended = () => { URL.revokeObjectURL(url); _currentAudio = null; console.log(`[voice] ${label} played OK`) }
  audio.onerror = (e) => { URL.revokeObjectURL(url); _currentAudio = null; console.error(`[voice] ${label} play error:`, e) }
  audio.play().catch(e => { console.error(`[voice] ${label} play() rejected:`, e); _currentAudio = null })
}

async function speak(text: string) {
  try {
    const res = await fetch('/api/voice/tts', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
    if (!res.ok) { console.error(`[voice] /tts HTTP ${res.status}`); return }
    const blob = await res.blob()
    if (blob.size === 0) { console.error('[voice] /tts returned empty blob'); return }
    playAudioBlob(blob, '/tts')
  } catch (e) {
    console.error('[voice] speak() error:', e)
    _currentAudio = null
  }
}

function stopSpeaking() {
  _currentAudio?.pause()
  _currentAudio = null
}

export function VoiceControl() {
  const { t } = useTranslation('stamp')
  const [listening, setListening] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [logs, setLogs] = useState<string[]>([])
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const startListening = useCallback(async () => {
    unlockAudio()
    if (_currentAudio) { stopSpeaking(); setSpeaking(false) }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')
          ? 'audio/ogg;codecs=opus'
          : 'audio/webm'
      const recorder = new MediaRecorder(stream, { mimeType })
      recorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }

      recorder.onstop = async () => {
        const webmBlob = new Blob(chunksRef.current, { type: mimeType })
        stream.getTracks().forEach(t => t.stop())
        setProcessing(true)
        setSpeaking(false)
        try {
          const formData = new FormData()
          formData.append('audio', webmBlob, 'voice.webm')
          const res = await fetch('/api/voice/chat', { method: 'POST', credentials: 'include', body: formData })
          if (!res.ok) {
            const text = await res.text()
            throw new Error(`HTTP ${res.status}: ${text}`)
          }
          const data = await res.json() as { tool_id?: number; comment?: string; audio?: string }
          const text = data.comment || ''
          setLogs(prev => [...prev, `> ${text}`])
          setSpeaking(true)
          if (data.audio) {
            // 后端返回了 TTS 音频（base64），直接播放
            try {
              const blob = new Blob([Uint8Array.from(atob(data.audio), c => c.charCodeAt(0))], { type: 'audio/wav' })
              playAudioBlob(blob, 'cached')
            } catch (e) {
              console.error('[voice] base64 decode error:', e)
              await speak(text)
            }
          } else if (text) {
            await speak(text)
          }
          setSpeaking(false)
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err)
          setLogs(prev => [...prev, `  ! ${t('voiceRecognitionFailed')}: ${msg}`])
        } finally {
          setProcessing(false)
        }
      }

      recorder.start()
      setListening(true)
      setLogs(prev => [...prev, `> ${t('recording')}`])
    } catch {
      setLogs(prev => [...prev, `  ! ${t('noMicrophoneAccess')}`])
    }
  }, [t])

  const stopListening = () => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') recorderRef.current.stop()
    if (streamRef.current) { streamRef.current.getTracks().forEach(t => t.stop()); streamRef.current = null }
    setListening(false)
  }

  return (
    <div className="w-full">
      <div className="flex items-center gap-3 mb-3">
        <button
          onMouseDown={startListening}
          onMouseUp={stopListening}
          onTouchStart={startListening}
          onTouchEnd={stopListening}
          disabled={processing}
          className={cn(
            'w-12 h-12 rounded-full border-2 flex items-center justify-center transition-all duration-150 ease-out select-none cursor-pointer',
            listening
              ? 'border-destructive bg-destructive/10 scale-105'
              : 'border-border bg-card hover:border-primary hover:bg-primary/5',
            speaking && 'border-success bg-success/10',
            'disabled:opacity-40 disabled:cursor-not-allowed',
          )}
        >
          <span className="text-lg">{listening ? '●' : '○'}</span>
        </button>
        <div>
          <div className="text-sm font-medium text-foreground">
            {listening ? t('recording') : processing ? t('recognizing') : speaking ? t('replying') : t('holdToSpeak')}
          </div>
          <div className="text-xs text-muted-foreground">{t('voiceControlHint')}</div>
        </div>
      </div>

      {logs.length > 0 && (
        <div className="bg-foreground rounded-md p-2.5 text-left font-mono text-[11px] max-h-[120px] overflow-y-auto leading-relaxed">
          {logs.map((log, i) => (
            <div key={i} className="py-px text-muted-foreground/80">{log}</div>
          ))}
        </div>
      )}
    </div>
  )
}