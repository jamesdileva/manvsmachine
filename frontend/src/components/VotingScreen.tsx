import { Clock, Loader2, Vote } from 'lucide-react'
import { useEffect, useId } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { URGENT_THRESHOLD, useTimer } from '@/hooks/useTimer'
import { cn } from '@/lib/utils'

/** Soft-nudge window: no hard lock-out — the server does not enforce it (Sprint 14). */
export const VOTING_WINDOW_SECONDS = 10

interface VotingScreenProps {
  /** Anonymized entries: {A: "text", B: "text"}. */
  entries: Record<string, string> | null
  onVote: (letter: string) => void
  /** Hides the buttons after the player has voted. */
  disabled?: boolean
  className?: string
}

export function VotingScreen({
  entries,
  onVote,
  disabled = false,
  className,
}: VotingScreenProps) {
  const timer = useTimer()
  const titleId = useId()

  // Restart the soft-nudge window whenever a new pair of entries arrives.
  useEffect(() => {
    if (entries) timer.start(VOTING_WINDOW_SECONDS)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entries])

  if (!entries) {
    return (
      <Card className={className} data-testid="voting-screen">
        <CardContent className="flex items-center gap-2 py-10 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Waiting for the other entry…
        </CardContent>
      </Card>
    )
  }

  const letters = Object.keys(entries).sort()
  const urgent = timer.secondsLeft <= URGENT_THRESHOLD

  return (
    <div className={cn('space-y-3', className)} data-testid="voting-screen">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold" id={titleId}>
          Which entry is the AI?
        </h2>
        <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Clock className="h-3.5 w-3.5" aria-hidden />
          <span
            className={cn(
              'font-mono tabular-nums',
              urgent && 'text-destructive',
            )}
          >
            {timer.secondsLeft}s
          </span>
        </span>
      </div>

      <div
        className="grid gap-3 sm:grid-cols-2"
        role="group"
        aria-labelledby={titleId}
      >
        {letters.map((letter) => (
          <Card key={letter} data-testid={`entry-${letter}`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">
                Entry {letter}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="whitespace-pre-wrap text-sm">{entries[letter]}</p>
              <Button
                variant="outline"
                className="w-full"
                disabled={disabled}
                onClick={() => onVote(letter)}
              >
                <Vote className="h-4 w-4" aria-hidden />
                {letter} is the AI
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {timer.isExpired && (
        <p className="text-sm text-muted-foreground" data-testid="voting-nudge">
          Still deciding? Pick one — your vote counts whenever it lands.
        </p>
      )}
    </div>
  )
}
