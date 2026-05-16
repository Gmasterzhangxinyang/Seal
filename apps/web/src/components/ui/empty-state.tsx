import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Inbox } from 'lucide-react'

interface EmptyStateProps {
  icon?: ReactNode
  title?: string
  description?: string
  action?: ReactNode
  className?: string
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 text-center', className)}>
      {icon || <Inbox className="h-10 w-10 text-muted-foreground/40" />}
      {title && <p className="mt-3 text-sm font-medium text-muted-foreground">{title}</p>}
      {description && <p className="mt-1 text-xs text-muted-foreground/70">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
