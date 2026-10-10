/**
 * Session state shape (Sprint 21 implements the provider).
 *
 * Placeholder per Sprint 18: the type + context exist so the game pages can be
 * built against the contract; the provider and the WebSocket-driven game loop
 * arrive with Sprint 19/21.
 */

import { createContext } from 'react'

import type { ChallengeDefinition, RoundStateInfo } from '@/types'

export type GameState =
  'idle' | 'writing' | 'reveal_ai' | 'voting' | 'score' | 'complete'

export interface SessionState {
  sessionId: string | null
  currentRound: RoundStateInfo | null
  challenge: ChallengeDefinition | null
  gameState: GameState
  timeRemaining: number
  entry: string
}

export const initialSessionState: SessionState = {
  sessionId: null,
  currentRound: null,
  challenge: null,
  gameState: 'idle',
  timeRemaining: 0,
  entry: '',
}

export const SessionContext = createContext<SessionState>(initialSessionState)
