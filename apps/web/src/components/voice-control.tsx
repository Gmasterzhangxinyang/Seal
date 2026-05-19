import { useState, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { apiPost } from '@/lib/api-client'
import { cn } from '@/lib/utils'

let _currentAudio: HTMLAudioElement | null = null

async function speak(text: string) {
  stopSpeaking()
  try {
    const res = await fetch('/api/voice/tts', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
    if (!res.ok) return
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    _currentAudio = audio
    audio.onended = () => { URL.revokeObjectURL(url); _currentAudio = null }
    audio.onerror = () => { URL.revokeObjectURL(url); _currentAudio = null }
    audio.play()
  } catch {
    _currentAudio = null
  }
}

function stopSpeaking() {
  _currentAudio?.pause()
  _currentAudio = null
}

let _sessionId = `voice-${Date.now()}`

export function VoiceControl() {
  const { t } = useTranslation('stamp')
  const [listening, setListening] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [logs, setLogs] = useState<string[]>([])
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const sendCommand = useCallback(async (text: string) => {
    if (!text.trim()) return
    setProcessing(true)
    setLogs((prev) => [...prev, `> ${text}`])
    try {
      const res = await apiPost<{
        reply: string
        action: string | null
        action_description: string | null
      }>('/voice/chat', { session_id: _sessionId, text })

      setLogs((prev) => {
        const next = [...prev]
        if (res.action_description) next.push(`  [${res.action_description}]`)
        if (res.reply) next.push(`  ${res.reply}`)
        return next
      })

      if (res.reply) {
        setSpeaking(true)
        speak(res.reply)
      }
    } catch {
      setLogs((prev) => [...prev, `  ! ${t('processFailed')}`])
    } finally {
      setProcessing(false)
    }
  }, [t])

  const startListening = useCallback(async () => {
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
        const blob = new Blob(chunksRef.current, { type: mimeType })
        stream.getTracks().forEach(t => t.stop())
        setProcessing(true)
        try {
          const res = await fetch('/api/voice/asr', { method: 'POST', credentials: 'include', body: blob })
          if (!res.ok) throw new Error('ASR failed')
          const data = await res.json() as { text: string }
          if (data.text?.trim()) sendCommand(data.text)
          else setProcessing(false)
        } catch {
          setLogs((prev) => [...prev, `  ! ${t('voiceRecognitionFailed')}`])
          setProcessing(false)
        }
      }

      recorder.start()
      setListening(true)
      setLogs((prev) => [...prev, `> ${t('recording')}`])
    } catch {
      setLogs((prev) => [...prev, `  ! ${t('noMicrophoneAccess')}`])
    }
  }, [sendCommand, t])

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
