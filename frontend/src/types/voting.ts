/** Voting and reveal types — mirror the backend schemas (Implementation Guide §2.7). */

export interface SubmitEntryRequest {
  challenge_id: string
  entry: string
}

export interface SubmitEntryResponse {
  challenge_id: string
  human_entry: string
  ai_entry: string
  provider: string
  model: string
  hard_violations: string[]
  soft_violations: string[]
}

export interface VoteRequest {
  round_id: string
  vote: string
}

/** Service-level vote acknowledgement (`VoteResult`). */
export interface VoteAck {
  round_id: string
  vote: string
  can_reveal: boolean
  total_votes: number
}

/** The round's attribution, humanity scores, and explanation. */
export interface RevealResult {
  round_id: string
  entries: Record<string, string>
  human_was: string
  ai_was: string
  vote: string | null
  vote_correct: boolean
  humanity_human: number
  humanity_ai: number
  explanation: string
}

/** The reveal plus the score and rating effects returned by `POST /voting/vote`. */
export interface VoteResponse extends RevealResult {
  base: number
  time_bonus: number
  streak_bonus: number
  total: number
  detection_rating: number
  streak: number
}
