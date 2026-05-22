import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'react'

export function Spinner({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('h-5 w-5 animate-spin rounded-full border-2 border-muted border-t-primary', className)}
      role="status"
      aria-label="loading"
      {...props}
    />
  )
}
