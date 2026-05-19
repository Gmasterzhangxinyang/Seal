import { createContext, useContext, type HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

interface TabsContextValue {
  value: string
  onValueChange: (value: string) => void
}

const TabsContext = createContext<TabsContextValue | null>(null)

function useTabs() {
  const ctx = useContext(TabsContext)
  if (!ctx) throw new Error('Tabs compound components must be used within <Tabs>')
  return ctx
}

interface TabsProps extends HTMLAttributes<HTMLDivElement> {
  value: string
  onValueChange: (value: string) => void
}

export function Tabs({ value, onValueChange, className, children, ...props }: TabsProps) {
  return (
    <TabsContext.Provider value={{ value, onValueChange }}>
      <div className={cn('flex flex-col gap-4', className)} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  )
}

export function TabsList({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex border-b border-border', className)}
      role="tablist"
      {...props}
    >
      {children}
    </div>
  )
}

interface TabsTriggerProps extends HTMLAttributes<HTMLButtonElement> {
  value: string
  count?: number
}

export function TabsTrigger({ value, count, className, children, ...props }: TabsTriggerProps) {
  const { value: selectedValue, onValueChange } = useTabs()
  const isActive = selectedValue === value

  return (
    <button
      role="tab"
      aria-selected={isActive}
      data-state={isActive ? 'active' : 'inactive'}
      className={cn(
        'relative px-4 py-2.5 text-sm font-medium transition-colors duration-150 ease-out cursor-pointer',
        'text-muted-foreground hover:text-foreground',
        isActive && 'text-foreground',
        className
      )}
      onClick={() => onValueChange(value)}
      {...props}
    >
      <span className="flex items-center gap-2">
        {children}
        {count !== undefined && (
          <span
            className={cn(
              'inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-xs font-medium',
              isActive ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
            )}
          >
            {count}
          </span>
        )}
      </span>
      {isActive && (
        <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full" />
      )}
    </button>
  )
}

interface TabsContentProps extends HTMLAttributes<HTMLDivElement> {
  value: string
}

export function TabsContent({ value, className, children, ...props }: TabsContentProps) {
  const { value: selectedValue } = useTabs()
  if (selectedValue !== value) return null

  return (
    <div
      role="tabpanel"
      data-state="active"
      className={cn('animate-fade-in', className)}
      {...props}
    >
      {children}
    </div>
  )
}
