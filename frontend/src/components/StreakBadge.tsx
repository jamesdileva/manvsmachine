import { Flame } from 'lucide-react'

import { cn } from '@/lib/utils'

interface StreakBadgeProps {
  /** Current consecutive-day streak. */
  days: number
  className?: string
}

export function StreakBadge({ days, className }: StreakBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border px-2.5 py-0.5 text-xs font-semibold',
        days > 0
          ? 'border-transparent bg-secondary text-secondary-foreground'
          : 'text-muted-foreground',
        className,
      )}
      data-testid="streak-badge"
    >
      <Flame
        className={cn('h-3.5 w-3.5', days > 0 && 'text-orange-500')}
        aria-hidden
      />
      {days}-day streak
    </span>
  )
}
