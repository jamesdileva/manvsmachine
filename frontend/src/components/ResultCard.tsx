/** ResultCard: the shareable end-of-session card — stats plus a share button (Sprint 25). */

import { HumanityMeter } from '@/components/HumanityMeter'
import { ShareButton } from '@/components/ShareButton'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { SessionSummaryResponse } from '@/types'

interface ResultCardProps {
  summary: SessionSummaryResponse
  className?: string
}

/** Average of a per-round humanity field, ignoring rounds with no score yet. */
function averageHumanity(
  rounds: SessionSummaryResponse['rounds'],
  key: 'humanity_human' | 'humanity_ai',
): number {
  const values = rounds
    .map((round) => round[key])
    .filter((value): value is number => value !== null)
  if (values.length === 0) return 0
  return Math.round(
    values.reduce((total, value) => total + value, 0) / values.length,
  )
}

/** End-of-session card: score, accuracy, average humanity, and the share action. */
export function ResultCard({ summary, className }: ResultCardProps) {
  const correct = summary.rounds.filter((round) => round.correct).length

  return (
    <Card className={className} data-testid="result-card">
      <CardHeader>
        <CardTitle>Your result</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-6">
          <div>
            <p
              className="text-3xl font-bold tabular-nums"
              data-testid="result-total"
            >
              {summary.total_score}
            </p>
            <p className="text-xs text-muted-foreground">points</p>
          </div>
          <div>
            <p
              className="text-3xl font-bold tabular-nums"
              data-testid="result-accuracy"
            >
              {summary.accuracy === null
                ? '—'
                : `${Math.round(summary.accuracy)}%`}
            </p>
            <p className="text-xs text-muted-foreground">
              accuracy ({correct}/{summary.rounds.length})
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Your entries</span>
            <span className="tabular-nums" data-testid="result-humanity-human">
              {averageHumanity(summary.rounds, 'humanity_human')}
            </span>
          </div>
          <HumanityMeter
            score={averageHumanity(summary.rounds, 'humanity_human')}
            label="Your entries"
          />
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">AI entries</span>
            <span className="tabular-nums" data-testid="result-humanity-ai">
              {averageHumanity(summary.rounds, 'humanity_ai')}
            </span>
          </div>
          <HumanityMeter
            score={averageHumanity(summary.rounds, 'humanity_ai')}
            label="AI entries"
          />
          <p className="text-xs text-muted-foreground">
            How human your entries read versus the AI's, 0-100.
          </p>
        </div>

        <ShareButton sessionId={summary.session_id} />
      </CardContent>
    </Card>
  )
}
