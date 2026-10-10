import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'

import { cn } from '@/lib/utils'

interface RatingDisplayProps {
  rating: number
  /** Change from the last round (positive = gained). */
  change?: number
  className?: string
}

export function RatingDisplay({
  rating,
  change = 0,
  className,
}: RatingDisplayProps) {
  const rounded = Math.round(rating)
  const gained = change > 0
  const lost = change < 0
  const Icon = gained ? ArrowUpRight : lost ? ArrowDownRight : Minus

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-semibold tabular-nums',
        className,
      )}
      data-testid="rating-display"
    >
      {rounded.toLocaleString()}
      <span
        className={cn(
          'inline-flex items-center text-xs font-medium',
          gained && 'text-green-600',
          lost && 'text-destructive',
          !gained && !lost && 'text-muted-foreground',
        )}
        data-testid="rating-change"
      >
        <Icon className="h-3.5 w-3.5" aria-hidden />
        {change === 0 ? '±0' : ` ${Math.abs(Math.round(change))}`}
      </span>
    </span>
  )
}
