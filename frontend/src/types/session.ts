/** Session and round types — mirror the backend schemas (Implementation Guide §2.3). */

import type { RevealResult } from '@/types/voting'

export type SessionType = 'daily' | 'practice'

/** Round lifecycle states (the server-side state machine). */
export type RoundState = 'writing' | 'reveal_ai' | 'voting' | 'scored'

export interface SessionStartRequest {
  type: SessionType
  challenge_ids?: string[] | null
}

export interface RoundEntryRequest {
  entry: string
}

export interface ChallengeBrief {
  id: string
  prompt: string
  time_limit_seconds: number
}

export interface SessionStartResponse {
  session_id: string
  type: string
  rounds_total: number
  next_challenge: ChallengeBrief
  round_id: string | null
}

export interface SessionStateResponse {
  session_id: string
  type: string
  current_round: number
  rounds_total: number
  state: string
  started_at: string
  completed_at: string | null
}

export interface RoundSummary {
  round_number: number
  challenge_id: string
  vote: string | null
  correct: boolean | null
  score: number | null
  humanity_human: number | null
  humanity_ai: number | null
}

export interface SessionSummaryResponse {
  session_id: string
  type: string
  total_score: number
  accuracy: number | null
  rounds: RoundSummary[]
  rating_change: number | null
  streak: number | null
}

export interface DailyChallengeResponse {
  challenge: import('@/types/challenge').ChallengeOut
  session_id: string
  round_number: number
  round_id: string | null
}

export interface RoundScore {
  vote_correct: boolean
  base: number
  time_bonus: number
  streak_bonus: number
  total: number
}

/** The round a player is about to play. */
export interface RoundStateInfo {
  round_id: string
  challenge: ChallengeBrief
  round_number: number
  rounds_total: number
  state: RoundState
}

export interface NextRoundResponse {
  complete: boolean
  round: RoundStateInfo | null
}

/** Both entries for a round, anonymized as A/B (no attribution). */
export interface RoundSubmission {
  round_id: string
  entries: Record<string, string>
  ai_provider: string
  ai_model: string
  hard_violations: string[]
  soft_violations: string[]
}

/** Vote outcome: the reveal plus the round's score and rating effects. */
export interface RoundResult {
  round_id: string
  reveal: RevealResult
  score: RoundScore
  rating: number
  rating_change: number
  streak: number
}

/** WebSocket `SESSION_STARTED` payload (camelCase — see §3.2). */
export interface SessionOverview {
  sessionId: string
  rounds: number
  roundsPlayed: number
  completed: boolean
  challenges: ChallengeBrief[]
}
