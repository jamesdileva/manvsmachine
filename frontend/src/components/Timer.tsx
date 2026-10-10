import { cn } from '@/lib/utils'

interface TimerProps {
  secondsLeft: number
  totalSeconds: number
  isRunning?: boolean
  className?: string
}

/** Countdown ring-free display: green normally, yellow inside 10s, red at 5s. */
export function Timer({
  secondsLeft,
  totalSeconds,
  isRunning = true,
  className,
}: TimerProps) {
  const urgent = secondsLeft <= 5
  const warning = !urgent && secondsLeft <= 10
  const percent =
    totalSeconds > 0
      ? Math.max(0, Math.min(100, (secondsLeft / totalSeconds) * 100))
      : 0

  return (
    <div
      className={cn('flex items-center gap-3', className)}
      data-testid="timer"
    >
      <div
        className="h-2 flex-1 overflow-hidden rounded-full bg-secondary"
        role="progressbar"
        aria-label="Time remaining"
        aria-valuenow={secondsLeft}
        aria-valuemin={0}
        aria-valuemax={totalSeconds}
      >
        <div
          className={cn(
            'h-full transition-all duration-300',
            urgent
              ? 'bg-destructive'
              : warning
                ? 'bg-yellow-500'
                : 'bg-primary',
          )}
          style={{ width: `${percent}%` }}
        />
      </div>
      <span
        className={cn(
          'w-10 text-right font-mono text-lg font-semibold tabular-nums',
          urgent
            ? 'text-destructive'
            : warning
              ? 'text-yellow-600'
              : 'text-foreground',
        )}
        data-testid="timer-seconds"
      >
        {secondsLeft}
      </span>
      {!isRunning && secondsLeft === 0 && (
        <span className="text-sm text-destructive">Time!</span>
      )}
    </div>
  )
}
