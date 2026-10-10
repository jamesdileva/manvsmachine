import { useEffect, useState } from 'react'

import { cn } from '@/lib/utils'
import type { RoundScore } from '@/types'

interface ScoreAnimationProps {
  score: RoundScore
  /** Count-up duration in ms. */
  duration?: number
  className?: string
}

/** Animated score readout: counts up to the total, then shows the breakdown. */
export function ScoreAnimation({
  score,
  duration = 800,
  className,
}: ScoreAnimationProps) {
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    if (duration <= 0) {
      setDisplay(score.total)
      return
    }
    const steps = Math.max(1, Math.round(duration / 50))
    let step = 0
    const interval = setInterval(() => {
      step += 1
      const ratio = Math.min(1, step / steps)
      setDisplay(Math.round(score.total * ratio))
      if (ratio >= 1) clearInterval(interval)
    }, 50)
    return () => clearInterval(interval)
  }, [score.total, duration])

  const rows = [
    {
      label: score.vote_correct ? 'Correct detection' : 'Detection missed',
      value: score.base,
    },
    { label: 'Speed bonus', value: score.time_bonus },
    { label: 'Streak bonus', value: score.streak_bonus },
  ]

  return (
    <div className={cn('space-y-3', className)} data-testid="score-animation">
      <p className="text-4xl font-bold tabular-nums" data-testid="score-total">
        {display}
      </p>
      <dl className="space-y-1 text-sm">
        {rows.map((row) => (
          <div key={row.label} className="flex justify-between">
            <dt className="text-muted-foreground">{row.label}</dt>
            <dd className="tabular-nums">+{row.value}</dd>
          </div>
        ))}
        <div className="flex justify-between border-t pt-1 font-semibold">
          <dt>Total</dt>
          <dd className="tabular-nums" data-testid="score-breakdown-total">
            {score.total}
          </dd>
        </div>
      </dl>
    </div>
  )
}
