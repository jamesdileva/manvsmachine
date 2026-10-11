/** HumanityMeter: 0-100 bar for how human-like an entry reads (AGENTS.md rule 5). */

import { cn } from '@/lib/utils'

interface HumanityMeterProps {
  /** Humanity score in the 0-100 range; values outside it are clamped. */
  score: number
  /** Names the meter for screen readers (e.g. a challenge id or "Your entries"). */
  label?: string
  className?: string
}

export function HumanityMeter({
  score,
  label = 'Your entries',
  className,
}: HumanityMeterProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)))
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div
        role="progressbar"
        aria-label={`${label} humanity score`}
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        className="relative h-2.5 w-full overflow-hidden rounded-full bg-secondary"
      >
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${clamped}%` }}
        />
      </div>
      <span
        className="w-10 shrink-0 text-right text-sm font-medium tabular-nums"
        data-testid="humanity-value"
      >
        {clamped}
      </span>
    </div>
  )
}
