import { useState, useRef, useCallback } from 'react'
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
    setLogs((prev) => [...prev, `🎤 ${text}`])
    try {
      const res = await apiPost<{
        reply: string
        action: string | null
        action_description: string | null
      }>('/voice/chat', { session_id: _sessionId, text })

      setLogs((prev) => {
        const next = [...prev]
        if (res.action_description) {
          next.push(`⚙️ ${res.action_description}`)
        }
        if (res.reply) {
          next.push(`🤖 ${res.reply}`)
        }
        return next
      })

      if (res.reply) {
        setSpeaking(true)
        speak(res.reply)
      }
    } catch {
      setLogs((prev) => [...prev, '❌ 处理失败'])
    } finally {
      setProcessing(false)
    }
  }, [])

  const startListening = useCallback(async () => {
    if (_currentAudio) {
      stopSpeaking()
      setSpeaking(false)
    }

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

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: mimeType })
        stream.getTracks().forEach(t => t.stop())
        setProcessing(true)

        try {
          const res = await fetch('/api/voice/asr', {
            method: 'POST',
            credentials: 'include',
            body: blob,
          })

          if (!res.ok) throw new Error('ASR failed')
          const data = await res.json() as { text: string }
          if (data.text?.trim()) {
            sendCommand(data.text)
          } else {
            setProcessing(false)
          }
        } catch {
          setLogs((prev) => [...prev, '❌ 语音识别失败'])
          setProcessing(false)
        }
      }

      recorder.start()
      setListening(true)
      setLogs((prev) => [...prev, '🎤 开始录音...'])
    } catch {
      setLogs((prev) => [...prev, '❌ 无法访问麦克风'])
    }
  }, [sendCommand])

  const stopListening = () => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop()
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    setListening(false)
  }

  return (
    <div className="max-w-[480px] mx-auto">
      <div className="flex items-center justify-center gap-3 mb-3">
        <button
          onMouseDown={startListening}
          onMouseUp={stopListening}
          onTouchStart={startListening}
          onTouchEnd={stopListening}
          disabled={processing}
          className={cn(
            'w-16 h-16 rounded-full border-2 flex items-center justify-center text-3xl transition-all select-none',
            listening
              ? 'border-red-500 bg-red-50 scale-110'
              : 'border-gray-300 bg-white hover:border-[#457b9d] hover:bg-blue-50',
            speaking && 'border-green-500 bg-green-50',
            'disabled:opacity-50 disabled:cursor-not-allowed',
          )}
        >
          {listening ? '🔴' : '🎤'}
        </button>
        <div className="text-sm">
          <div className="font-medium text-gray-700">
            {listening ? '录音中...' : processing ? '识别中...' : speaking ? '回复中...' : '按住说话'}
          </div>
          <div className="text-xs text-gray-400 mt-0.5">语音对话 · 按住说话，松开识别</div>
        </div>
      </div>

      {logs.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-3 text-left font-mono text-xs max-h-[160px] overflow-y-auto">
          {logs.map((log, i) => (
            <div key={i} className="py-0.5 text-gray-400">{log}</div>
          ))}
        </div>
      )}
    </div>
  )
}