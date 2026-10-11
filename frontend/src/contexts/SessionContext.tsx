/**
 * SessionContext: the 3-round game loop.
 *
 * Owns the session lifecycle, the entry text, the round clock, and the
 * game-state machine on top of the live channel (VotingContext). The server
 * drives the flow — it broadcasts the next ROUND_START (or SESSION_END) right
 * after scoring — so this context only sequences the *presentation*: it holds
 * the score for a beat before moving on, and auto-submits the entry when the
 * clock runs out.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

import { toApiError } from '@/api/errors'
import { sessionApi } from '@/api/session'
import { useChallenges } from '@/hooks/useChallenges'
import { useTimer } from '@/hooks/useTimer'
import { useVotingContext } from '@/contexts/VotingContext'
import type {
  ChallengeDefinition,
  SessionOverview,
  SessionStartRequest,
  SessionStartResponse,
} from '@/types'

export type GameState =
  'idle' | 'writing' | 'reveal_ai' | 'voting' | 'score' | 'complete'

/** How long the score stays up before the next round starts. */
const SCORE_DWELL_MS = 2500

export interface SessionContextValue {
  session: SessionOverview | null
  sessionId: string | null
  currentRoundNumber: number
  roundsTotal: number
  challenge: ChallengeDefinition | null
  gameState: GameState
  timeRemaining: number
  entry: string
  error: string | null
  setEntry: (entry: string) => void
  startSession: (
    body?: SessionStartRequest,
  ) => Promise<SessionStartResponse | null>
  submitEntry: (entry?: string) => void
  submitVote: (letter: string) => void
  /** Manual advance (the socket already advances automatically after scoring). */
  nextRound: () => Promise<void>
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({
  children,
  scoreDwellMs = SCORE_DWELL_MS,
}: {
  children: ReactNode
  /** Override the post-score dwell (tests pass 0 to skip the wait). */
  scoreDwellMs?: number
}) {
  const voting = useVotingContext()
  const { challenge, loadChallenge } = useChallenges()
  const [gameState, setGameState] = useState<GameState>('idle')
  const [entry, setEntry] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [dwellUntil, setDwellUntil] = useState(0)

  const roundId = voting.round?.roundId ?? null
  const seenRoundId = useRef<string | null>(null)
  /** The first round's id, from the REST start response (before ROUND_START arrives). */
  const startRoundId = useRef<string | null>(null)
  const appliedScoreRound = useRef<string | null>(null)
  const entryRef = useRef(entry)
  entryRef.current = entry

  const submitEntry = useCallback(
    (value?: string) => {
      const round = voting.round?.roundId ?? startRoundId.current
      if (!round) return
      const text = value ?? entryRef.current
      voting.submitEntry(round, text)
      setEntry('')
    },
    [voting],
  )

  // The clock auto-submits whatever the player has when it runs out.
  const timer = useTimer(() => submitEntry())

  const submitVote = useCallback(
    (letter: string) => {
      const round = voting.round?.roundId ?? startRoundId.current
      if (round) voting.vote(round, letter)
    },
    [voting],
  )

  const startSession = useCallback(
    async (body: SessionStartRequest = { type: 'daily' }) => {
      setError(null)
      setGameState('idle')
      seenRoundId.current = null
      appliedScoreRound.current = null
      try {
        const response = await sessionApi.start(body)
        voting.connect(response.session_id)
        if (response.next_challenge) {
          void loadChallenge(response.next_challenge.id)
        }
        // Enter the round immediately; the socket's ROUND_START confirms it.
        // (Prevents a blank page while the channel opens.)
        if (response.round_id) {
          startRoundId.current = response.round_id
          seenRoundId.current = response.round_id
          setGameState('writing')
        }
        return response
      } catch (caught) {
        setError(toApiError(caught).message)
        return null
      }
    },
    [voting, loadChallenge],
  )

  const nextRound = useCallback(async () => {
    if (!voting.session) return
    try {
      await sessionApi.next(voting.session.sessionId)
    } catch (caught) {
      setError(toApiError(caught).message)
    }
  }, [voting.session])

  // New round -> writing (the score dwell owns the transition out of 'score').
  useEffect(() => {
    if (gameState === 'score') return
    if (roundId && roundId !== seenRoundId.current) {
      seenRoundId.current = roundId
      setGameState('writing')
      setEntry('')
    }
  }, [roundId, gameState])

  // Both entries in -> voting.
  useEffect(() => {
    if (voting.entries && gameState === 'writing') setGameState('voting')
  }, [voting.entries, gameState])

  // Reveal in (before the score lands) -> reveal_ai.
  useEffect(() => {
    if (voting.reveal && (gameState === 'voting' || gameState === 'writing')) {
      setGameState('reveal_ai')
    }
  }, [voting.reveal, gameState])

  // Score in -> hold the score, then move on (once per round: the score stays
  // in context after the dwell applies, so a stale score must not re-fire).
  useEffect(() => {
    if (!voting.score) return
    const scoredRound = voting.round?.roundId ?? null
    if (gameState !== 'score' && appliedScoreRound.current !== scoredRound) {
      appliedScoreRound.current = scoredRound
      setGameState('score')
      setDwellUntil(Date.now() + scoreDwellMs)
    }
  }, [voting.score, gameState, scoreDwellMs, voting.round?.roundId])

  // The dwell timer applies whatever the socket delivered next. A single
  // timeout (not an interval): a new event re-runs the effect, which reschedules
  // with the remaining dwell, so the hold is exact and nothing polls.
  useEffect(() => {
    if (gameState !== 'score') return
    const apply = () => {
      if (voting.summary) {
        setGameState('complete')
      } else if (roundId && roundId !== seenRoundId.current) {
        seenRoundId.current = roundId
        setGameState('writing')
      }
    }
    const timer = setTimeout(apply, Math.max(0, dwellUntil - Date.now()))
    return () => clearTimeout(timer)
  }, [gameState, dwellUntil, voting.summary, roundId])

  // The round clock runs while the player is writing. The socket's time limit
  // wins; the loaded challenge's limit covers the gap before ROUND_START.
  useEffect(() => {
    const limit =
      voting.round?.timeLimitSeconds ?? challenge?.timeLimitSeconds ?? 0
    if (gameState === 'writing' && limit > 0) timer.start(limit)
    else timer.stop()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    gameState,
    voting.round?.roundId,
    voting.round?.timeLimitSeconds,
    challenge?.timeLimitSeconds,
  ])

  // Socket errors surface to the player.
  useEffect(() => {
    if (voting.error) setError(voting.error)
  }, [voting.error])

  const value = useMemo<SessionContextValue>(
    () => ({
      session: voting.session,
      sessionId: voting.session?.sessionId ?? null,
      currentRoundNumber: voting.round?.roundNumber ?? 0,
      roundsTotal: voting.round?.roundsTotal ?? voting.session?.rounds ?? 0,
      challenge,
      gameState,
      timeRemaining: timer.secondsLeft,
      entry,
      error,
      setEntry,
      startSession,
      submitEntry,
      submitVote,
      nextRound,
    }),
    [
      voting.session,
      voting.round,
      challenge,
      gameState,
      timer.secondsLeft,
      entry,
      error,
      startSession,
      submitEntry,
      submitVote,
      nextRound,
    ],
  )

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  )
}

export function useSessionContext(): SessionContextValue {
  const context = useContext(SessionContext)
  if (context === null) {
    throw new Error('useSessionContext must be used inside a SessionProvider')
  }
  return context
}
