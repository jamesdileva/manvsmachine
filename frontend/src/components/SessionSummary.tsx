import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { SessionSummaryResponse } from '@/types'

interface SessionSummaryProps {
  summary: SessionSummaryResponse
  className?: string
}

/** End-of-session recap: totals, accuracy, and the per-round breakdown. */
export function SessionSummary({ summary, className }: SessionSummaryProps) {
  const navigate = useNavigate()

  return (
    <Card className={className} data-testid="session-summary">
      <CardHeader>
        <CardTitle>Session complete</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-6">
          <div>
            <p
              className="text-3xl font-bold tabular-nums"
              data-testid="summary-total"
            >
              {summary.total_score}
            </p>
            <p className="text-xs text-muted-foreground">points</p>
          </div>
          <div>
            <p
              className="text-3xl font-bold tabular-nums"
              data-testid="summary-accuracy"
            >
              {summary.accuracy === null
                ? '—'
                : `${Math.round(summary.accuracy)}%`}
            </p>
            <p className="text-xs text-muted-foreground">accuracy</p>
          </div>
          <div>
            <p
              className="text-3xl font-bold tabular-nums"
              data-testid="summary-streak"
            >
              {summary.streak ?? 0}
            </p>
            <p className="text-xs text-muted-foreground">streak</p>
          </div>
        </div>

        <ol className="space-y-1 text-sm" data-testid="summary-rounds">
          {summary.rounds.map((round) => (
            <li key={round.round_number} className="flex justify-between">
              <span className="text-muted-foreground">
                Round {round.round_number} · {round.challenge_id}
              </span>
              <span className="tabular-nums">
                {round.score ?? 0} pts · {round.correct ? 'correct' : 'missed'}
              </span>
            </li>
          ))}
        </ol>

        <Button onClick={() => navigate('/')}>Play again</Button>
      </CardContent>
    </Card>
  )
}
