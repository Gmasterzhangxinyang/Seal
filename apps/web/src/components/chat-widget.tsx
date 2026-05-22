import { useEffect, useRef, useState } from 'react'
import { MessageCircle, Send, X } from 'lucide-react'
import { apiPost } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { useTranslation } from 'react-i18next'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ChatResponse {
  reply: string
}

export function ChatWidget() {
  const { t } = useTranslation('chat')
  const greeting = t('greeting')
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: greeting },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // keep the greeting in sync when language changes mid-session
  useEffect(() => {
    setMessages((prev) =>
      prev.length === 1 && prev[0].role === 'assistant'
        ? [{ role: 'assistant', content: greeting }]
        : prev.map((msg, i) =>
            i === 0 && msg.role === 'assistant' ? { ...msg, content: greeting } : msg,
          ),
    )
  }, [greeting])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async () => {
    const text = input.trim()
    if (!text || loading) return

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setLoading(true)

    try {
      const data = await apiPost<ChatResponse>('/chat', { message: text })
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: t('error') },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
      {open && (
        <div className="flex h-[420px] w-80 flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-xl">
          <div className="flex items-center justify-between bg-primary px-4 py-3 text-primary-foreground">
            <span className="text-sm font-medium">{t('title')}</span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-md p-1 hover:bg-primary-foreground/10"
              aria-label={t('close')}
            >
              <X size={16} />
            </button>
          </div>

          <div className="flex-1 space-y-2 overflow-y-auto p-3 text-sm">
            {messages.map((message, index) => (
              <div
                key={index}
                className={cn('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}
              >
                <div
                  className={cn(
                    'max-w-[75%] whitespace-pre-wrap rounded-xl px-3 py-2 leading-relaxed',
                    message.role === 'user'
                      ? 'rounded-br-none bg-primary text-primary-foreground'
                      : 'rounded-bl-none bg-muted text-foreground',
                  )}
                >
                  {message.content}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="rounded-xl rounded-bl-none bg-muted px-3 py-2 text-muted-foreground">
                  {t('thinking')}
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="flex items-center gap-2 border-t border-border p-3">
            <input
              className="min-w-0 flex-1 rounded-lg border border-border bg-background px-3 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary"
              placeholder={t('placeholder')}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') send()
              }}
            />
            <button
              type="button"
              onClick={send}
              disabled={loading || !input.trim()}
              className="rounded-lg bg-primary p-2 text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
              aria-label={t('send')}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform hover:scale-105"
        aria-label={t('open')}
      >
        <MessageCircle size={22} />
      </button>
    </div>
  )
}
