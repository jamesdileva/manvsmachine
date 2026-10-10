import { useEffect, useState } from 'react'

import { toApiError } from '@/api/errors'
import { sessionApi } from '@/api/session'
import { ChallengeView } from '@/components/ChallengeView'
import { EntryInput } from '@/components/EntryInput'
import { Timer } from '@/components/Timer'
import { VotingScreen } from '@/components/VotingScreen'
import { useScoringContext } from '@/contexts/ScoringContext'
import { useVotingContext } from '@/contexts/VotingContext'
import { useChallenges } from '@/hooks/useChallenges'
import { useTimer } from '@/hooks/useTimer'
import type { SessionStartResponse } from '@/types'

export default function Session() {
  const voting = useVotingContext()
  const scoring = useScoringContext()
  const { challenge, loadChallenge } = useChallenges()
  const [started, setStarted] = useState<SessionStartResponse | null>(null)
  const [entry, setEntry] = useState('')
  const [error, setError] = useState<string | null>(null)
  const timer = useTimer()

  // Start a daily session and open the live channel to it.
  useEffect(() => {
    let cancelled = false
    async function start() {
      try {
        const response = await sessionApi.start({ type: 'daily' })
        if (cancelled) return
        setStarted(response)
        voting.connect(response.session_id)
        if (response.next_challenge) {
          void loadChallenge(response.next_challenge.id)
          timer.start(response.next_challenge.time_limit_seconds)
        }
      } catch (caught) {
        if (!cancelled) setError(toApiError(caught).message)
      }
    }
    void start()
    return () => {
      cancelled = true
      voting.disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const roundId = voting.round?.roundId ?? started?.round_id ?? null

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Session</h1>
      {error && <p className="text-destructive">{error}</p>}

      {voting.status !== 'open' && (
        <p className="text-sm text-muted-foreground">
          Connecting to the session…
        </p>
      )}

      {challenge && (
        <div className="space-y-3">
          <ChallengeView challenge={challenge}>
            <Timer
              secondsLeft={timer.secondsLeft}
              totalSeconds={challenge.timeLimitSeconds}
              isRunning={timer.isRunning}
            />
            <EntryInput
              challenge={challenge}
              value={entry}
              onChange={setEntry}
              onSubmit={(value) =>
                roundId && voting.submitEntry(roundId, value)
              }
              disabled={voting.entries !== null}
            />
          </ChallengeView>
        </div>
      )}

      {/* Waiting / voting / revealed states for the current round. */}
      {voting.reveal === null && (
        <VotingScreen
          entries={voting.entries}
          onVote={(letter) => roundId && voting.vote(roundId, letter)}
          disabled={!roundId}
        />
      )}

      {voting.reveal && (
        <div className="space-y-1" data-testid="round-reveal">
          <p>
            Entry <strong>{voting.reveal.humanWas}</strong> was yours;{' '}
            <strong>{voting.reveal.aiWas}</strong> was the AI —{' '}
            {voting.reveal.voteCorrect
              ? 'nice catch!'
              : 'the machine fooled you.'}
          </p>
          <p className="text-sm text-muted-foreground">
            {voting.reveal.explanation}
          </p>
          {scoring.score && (
            <p className="text-sm">
              Score <strong>{scoring.score.score.total}</strong> · rating{' '}
              {scoring.ratingChange >= 0 ? '+' : ''}
              {scoring.ratingChange}
            </p>
          )}
        </div>
      )}

      {voting.summary && (
        <p className="text-sm text-muted-foreground">
          Session complete — total {voting.summary.total_score} points.
        </p>
      )}
    </div>
  )
}
