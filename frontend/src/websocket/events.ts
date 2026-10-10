/** Typed WebSocket events (Implementation Guide §3.2 / Master Architecture §16.1). */

import type {
  ChallengeBrief,
  RoundScore,
  SessionOverview,
  SessionSummaryResponse,
} from '@/types'

export const ServerEvent = {
  SESSION_STARTED: 'SESSION_STARTED',
  ROUND_START: 'ROUND_START',
  AI_RESPONSE_READY: 'AI_RESPONSE_READY',
  VOTE_CONFIRMED: 'VOTE_CONFIRMED',
  REVEAL: 'REVEAL',
  ROUND_SCORED: 'ROUND_SCORED',
  SESSION_END: 'SESSION_END',
  ERROR: 'ERROR',
  PONG: 'PONG',
} as const

export const ClientEvent = {
  SUBMIT_ENTRY: 'SUBMIT_ENTRY',
  VOTE: 'VOTE',
  PING: 'PING',
} as const

export type SessionStartedPayload = SessionOverview

export interface RoundStartPayload {
  roundId: string
  roundNumber: number
  roundsTotal: number
  challenge: ChallengeBrief
  timeLimitSeconds: number
  state: string
}

export interface AiResponseReadyPayload {
  roundId: string
  entries: Record<string, string>
}

export interface VoteConfirmedPayload {
  roundId: string
  vote: string
}

export interface RevealPayload {
  roundId: string
  humanWas: string
  aiWas: string
  vote: string | null
  voteCorrect: boolean
  humanityHuman: number
  humanityAI: number
  explanation: string
}

export interface RoundScoredPayload {
  roundId: string
  score: RoundScore
  ratingChange: number
  streakUpdate: number
}

export interface SessionEndPayload {
  sessionId: string
  summary: SessionSummaryResponse
}

export interface ErrorPayload {
  code: string
  message: string
}

export interface ServerEventMessage<T = unknown> {
  type: string
  data: T
}

export interface ClientEventMessage {
  type: string
  data: Record<string, unknown>
}
