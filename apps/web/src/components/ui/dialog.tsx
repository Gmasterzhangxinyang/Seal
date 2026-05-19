import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/utils'

interface DialogProps {
  open: boolean
  onClose: () => void
  children: ReactNode
}

export function Dialog({ open, onClose, children }: DialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="fixed inset-0 bg-foreground/40 animate-fade-in"
        onClick={onClose}
        aria-hidden
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal
        className={cn(
          'relative z-50 w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-lg animate-slide-up'
        )}
      >
        {children}
      </div>
    </div>,
    document.body
  )
}

interface DialogTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: ReactNode
}

export function DialogTitle({ className, children, ...props }: DialogTitleProps) {
  return (
    <h2 className={cn('text-base font-semibold', className)} {...props}>
      {children}
    </h2>
  )
}

interface DialogActionsProps extends React.HTMLAttributes<HTMLDivElement> {
  children: ReactNode
}

export function DialogActions({ className, children, ...props }: DialogActionsProps) {
  return (
    <div className={cn('mt-6 flex justify-end gap-2', className)} {...props}>
      {children}
    </div>
  )
}

export function useConfirm() {
  const resolveRef = useRef<((value: boolean) => void) | null>(null)

  function confirm(message: string): Promise<boolean> {
    return new Promise((resolve) => {
      resolveRef.current = resolve
    })
  }

  return { confirm }
}
