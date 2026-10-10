import { useEffect, useState } from 'react'

import { toApiError } from '@/api/errors'
import { sessionApi } from '@/api/session'
import { ChallengeView } from '@/components/ChallengeView'
import { EntryInput } from '@/components/EntryInput'
import { RatingDisplay } from '@/components/RatingDisplay'
import { RevealScreen } from '@/components/RevealScreen'
import { ScoreAnimation } from '@/components/ScoreAnimation'
import { SessionSummary } from '@/components/SessionSummary'
import { StreakBadge } from '@/components/StreakBadge'
import { Timer } from '@/components/Timer'
import { VotingScreen } from '@/components/VotingScreen'
import { useVotingContext } from '@/contexts/VotingContext'
import { useChallenges } from '@/hooks/useChallenges'
import { useTimer } from '@/hooks/useTimer'
import { useRoundState, useSessionEvents } from '@/websocket/hooks'
import type { SessionStartResponse } from '@/types'

/** Players start at the backend's default Detection Rating. */
const INITIAL_RATING = 1000

export default function Session() {
  const voting = useVotingContext()
  const { phase, round, timeLimitSeconds } = useRoundState()
  const session = useSessionEvents()
  const { challenge, loadChallenge } = useChallenges()
  const [started, setStarted] = useState<SessionStartResponse | null>(null)
  const [entry, setEntry] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [rating, setRating] = useState(INITIAL_RATING)
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

  // Track the Detection Rating from the per-round deltas.
  useEffect(() => {
    if (voting.score)
      setRating((current) => current + voting.score!.ratingChange)
  }, [voting.score])

  // The round clock runs while the player is writing.
  useEffect(() => {
    if (phase === 'writing' && timeLimitSeconds > 0)
      timer.start(timeLimitSeconds)
    else timer.stop()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, timeLimitSeconds, round?.roundId])

  const roundId = round?.roundId ?? started?.round_id ?? null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Session</h1>
        <div className="flex items-center gap-3">
          <StreakBadge days={voting.score?.streakUpdate ?? 0} />
          <RatingDisplay
            rating={rating}
            change={voting.score?.ratingChange ?? 0}
          />
        </div>
      </div>
      {error && <p className="text-destructive">{error}</p>}
      {voting.status !== 'open' && !session.isComplete && (
        <p className="text-sm text-muted-foreground">
          Connecting to the session…
        </p>
      )}

      {/* WRITING: the challenge, the clock, and the entry box. */}
      {challenge && phase === 'writing' && (
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
            onSubmit={(value) => roundId && voting.submitEntry(roundId, value)}
          />
        </ChallengeView>
      )}

      {/* VOTING: the anonymized pair until the player picks one. */}
      {voting.isVoting && (
        <VotingScreen
          entries={voting.entries}
          onVote={(letter) => roundId && voting.vote(roundId, letter)}
        />
      )}

      {/* REVEAL + SCORE. */}
      {voting.reveal && (
        <RevealScreen
          reveal={{ ...voting.reveal, entries: voting.entries ?? {} }}
        />
      )}
      {voting.score && <ScoreAnimation score={voting.score.score} />}

      {/* SESSION_END. */}
      {session.isComplete && voting.summary && (
        <SessionSummary summary={voting.summary} />
      )}
    </div>
  )
}
