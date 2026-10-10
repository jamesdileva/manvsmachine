/**
 * VotingContext: anonymized A/B entries, the player's vote, and the reveal.
 *
 * Backed by `useVoting` (the session WebSocket channel). Scoring state (score,
 * rating change, streaks, session summary) is exposed separately by
 * ScoringContext, which reads the same channel.
 */

import { createContext, useContext, useMemo, type ReactNode } from 'react'

import {
  useVoting,
  type VotingActions,
  type VotingState,
} from '@/hooks/useVoting'
import type { WebSocketFactory } from '@/websocket/client'

export interface VotingContextValue extends VotingState, VotingActions {
  /** True once both entries are in and the player has not voted yet. */
  isVoting: boolean
  vote: (roundId: string, letter: string) => void
}

const VotingContext = createContext<VotingContextValue | null>(null)

export function VotingProvider({
  children,
  socketFactory,
}: {
  children: ReactNode
  socketFactory?: WebSocketFactory
}) {
  const voting = useVoting(socketFactory)

  const value = useMemo<VotingContextValue>(
    () => ({
      ...voting,
      isVoting: voting.entries !== null && voting.reveal === null,
    }),
    [voting],
  )

  return (
    <VotingContext.Provider value={value}>{children}</VotingContext.Provider>
  )
}

export function useVotingContext(): VotingContextValue {
  const context = useContext(VotingContext)
  if (context === null) {
    throw new Error('useVotingContext must be used inside a VotingProvider')
  }
  return context
}
