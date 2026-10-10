/**
 * ScoringContext: round score, rating change, streaks, and session totals.
 *
 * Reads the same WebSocket channel as VotingContext (the providers nest), so
 * reveal/score/session-end events flow through without a second socket.
 */

import { createContext, useContext, useMemo, type ReactNode } from 'react'

import { useVotingContext } from '@/contexts/VotingContext'
import type { RoundScoredPayload } from '@/websocket/events'
import type { SessionSummaryResponse } from '@/types'

export interface ScoringContextValue {
  /** Latest round's score payload, or null before the first vote. */
  score: RoundScoredPayload | null
  /** Detection Rating change from the last round (positive = gained). */
  ratingChange: number
  streak: number
  summary: SessionSummaryResponse | null
}

const ScoringContext = createContext<ScoringContextValue | null>(null)

export function ScoringProvider({ children }: { children: ReactNode }) {
  const voting = useVotingContext()

  const value = useMemo<ScoringContextValue>(
    () => ({
      score: voting.score,
      ratingChange: voting.score?.ratingChange ?? 0,
      streak: voting.score?.streakUpdate ?? 0,
      summary: voting.summary,
    }),
    [voting.score, voting.summary],
  )

  return (
    <ScoringContext.Provider value={value}>{children}</ScoringContext.Provider>
  )
}

export function useScoringContext(): ScoringContextValue {
  const context = useContext(ScoringContext)
  if (context === null) {
    throw new Error('useScoringContext must be used inside a ScoringProvider')
  }
  return context
}
