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
    setError('connection_error')
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
    <div className={cn('relative bg-muted aspect-video rounded-lg overflow-hidden', className)}>
      {(!loaded || error) && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-muted gap-2 z-10">
          <div className="w-7 h-7 border-2 border-muted-foreground/20 border-t-primary rounded-full animate-spin" />
          <p className="text-muted-foreground text-xs">
            {!loaded && !error ? 'Connecting...' : 'Reconnecting...'}
          </p>
        </div>
      )}
      <img
        ref={imgRef}
        src="/api/cameras/video_feed"
        alt="Camera feed"
        className="w-full h-full object-contain"
        onError={handleError}
        onLoad={handleLoad}
      />
    </div>
  )
}
