import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface TooltipProps {
  content: ReactNode
  children: ReactNode
  side?: 'top' | 'bottom'
  className?: string
}

export function Tooltip({ content, children, side = 'top', className }: TooltipProps) {
  return (
    <span className="relative group inline-flex">
      {children}
      <span
        className={cn(
          'absolute z-50 left-1/2 -translate-x-1/2 px-2 py-1 text-xs rounded-md bg-foreground text-background whitespace-nowrap',
          'opacity-0 group-hover:opacity-100 transition-opacity duration-150 ease-out pointer-events-none',
          side === 'top' ? 'bottom-full mb-1.5' : 'top-full mt-1.5',
          className
        )}
      >
        {content}
      </span>
    </span>
  )
}
