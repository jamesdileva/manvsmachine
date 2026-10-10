/**
 * Round/session views over the live WebSocket channel.
 *
 * `useRoundState` derives the current round's phase from the socket events;
 * `useSessionEvents` exposes the session-level lifecycle (start/end).
 */

import { useVotingContext } from '@/contexts/VotingContext'
import type { RoundStartPayload } from '@/websocket/events'

export type RoundPhase = 'idle' | 'writing' | 'voting' | 'revealed' | 'scored'

export interface RoundView {
  phase: RoundPhase
  round: RoundStartPayload | null
  challengeId: string | null
  timeLimitSeconds: number
  entries: Record<string, string> | null
}

/** The round the player is in, as a single phase value for the UI to switch on. */
export function useRoundState(): RoundView {
  const { round, entries, reveal, score } = useVotingContext()

  const phase: RoundPhase = score
    ? 'scored'
    : reveal
      ? 'revealed'
      : entries
        ? 'voting'
        : round
          ? 'writing'
          : 'idle'

  return {
    phase,
    round,
    challengeId: round?.challenge.id ?? null,
    timeLimitSeconds: round?.timeLimitSeconds ?? 0,
    entries,
  }
}

export interface SessionView {
  sessionId: string | null
  roundsTotal: number
  roundsPlayed: number
  isComplete: boolean
}

/** Session lifecycle: the handshake payload plus the end-of-session summary. */
export function useSessionEvents(): SessionView {
  const { session, summary } = useVotingContext()
  return {
    sessionId: session?.sessionId ?? null,
    roundsTotal: session?.rounds ?? 0,
    roundsPlayed: session?.roundsPlayed ?? 0,
    isComplete: summary !== null,
  }
}
