import { useEffect, useState } from 'react'

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
import { useSession } from '@/hooks/useSession'

/** Players start at the backend's default Detection Rating. */
const INITIAL_RATING = 1000

/**
 * The session page: swaps between the writing, voting, reveal/score, and
 * summary views driven by SessionContext's game state.
 */
export default function Session() {
  const {
    challenge,
    gameState,
    timeRemaining,
    entry,
    setEntry,
    submitEntry,
    submitVote,
    startSession,
    error,
  } = useSession()
  const voting = useVotingContext()
  const [rating, setRating] = useState(INITIAL_RATING)

  // Open the channel + first round on mount.
  useEffect(() => {
    void startSession()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Track the Detection Rating from the per-round deltas.
  useEffect(() => {
    if (voting.score)
      setRating((current) => current + voting.score!.ratingChange)
  }, [voting.score])

  if (gameState === 'idle') {
    return <p className="text-muted-foreground">Starting your session…</p>
  }

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

      {gameState === 'writing' && challenge && (
        <ChallengeView challenge={challenge}>
          <Timer
            secondsLeft={timeRemaining}
            totalSeconds={challenge.timeLimitSeconds}
            isRunning={timeRemaining > 0}
          />
          <EntryInput
            challenge={challenge}
            value={entry}
            onChange={setEntry}
            onSubmit={(value) => submitEntry(value)}
          />
        </ChallengeView>
      )}

      {gameState === 'voting' && (
        <VotingScreen
          entries={voting.entries}
          onVote={submitVote}
          disabled={!voting.round}
        />
      )}

      {(gameState === 'reveal_ai' || gameState === 'score') &&
        voting.reveal && (
          <RevealScreen
            reveal={{ ...voting.reveal, entries: voting.entries ?? {} }}
          />
        )}

      {gameState === 'score' && voting.score && (
        <ScoreAnimation score={voting.score.score} />
      )}

      {gameState === 'complete' && voting.summary && (
        <SessionSummary summary={voting.summary} />
      )}
    </div>
  )
}
