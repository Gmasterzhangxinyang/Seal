import { cn } from '@/lib/utils'
import type { InputHTMLAttributes } from 'react'

interface SliderProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  valueLabel?: string
}

export function Slider({ className, label, valueLabel, ...props }: SliderProps) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      {(label || valueLabel) && (
        <div className="flex items-center justify-between text-sm">
          {label && <span className="font-medium text-foreground">{label}</span>}
          {valueLabel !== undefined && (
            <span className="font-mono text-xs text-muted-foreground tabular-nums">{valueLabel}</span>
          )}
        </div>
      )}
      <input
        type="range"
        className={cn(
          'w-full h-1.5 rounded-full appearance-none cursor-pointer',
          'bg-muted accent-primary',
          '[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:shadow-sm [&::-webkit-slider-thumb]:transition-shadow [&::-webkit-slider-thumb]:hover:shadow-md',
          '[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-primary [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:shadow-sm'
        )}
        {...props}
      />
    </div>
  )
}
