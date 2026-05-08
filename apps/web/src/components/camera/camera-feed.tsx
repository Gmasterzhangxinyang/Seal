import { useRef, useState, useCallback } from 'react'
import { cn } from '@/lib/utils'

interface CameraFeedProps {
  className?: string
}

export function CameraFeed({ className }: CameraFeedProps) {
  const imgRef = useRef<HTMLImageElement>(null)
  const [loaded, setLoaded] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const handleError = useCallback(() => {
    setError('连接失败')
    setLoaded(false)
    const delay = Math.min(2000 * Math.pow(1.5, retryCount), 10000)
    setTimeout(() => {
      if (imgRef.current) {
        imgRef.current.src = `/api/cameras/video_feed?t=${Date.now()}`
        setRetryCount((c) => c + 1)
      }
    }, delay)
  }, [retryCount])

  const handleLoad = useCallback(() => {
    setError(null)
    setLoaded(true)
    setRetryCount(0)
  }, [])

  return (
    <div className={cn('relative bg-gray-100 aspect-video rounded-lg', className)}>
      {(!loaded || error) && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-100 rounded-lg gap-2 z-10">
          <div className="w-8 h-8 border-4 border-gray-200 border-t-[#457b9d] rounded-full animate-spin" />
          <p className="text-gray-400 text-sm">
            {error ? `${error}，正在重连...` : '正在连接摄像头...'}
          </p>
        </div>
      )}
      <img
        ref={imgRef}
        src="/api/cameras/video_feed"
        alt="摄像头预览"
        className="w-full h-full object-contain rounded-lg shadow-lg"
        onError={handleError}
        onLoad={handleLoad}
      />
    </div>
  )
}
